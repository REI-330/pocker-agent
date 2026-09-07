import json

import httpx2
import pytest
from openai import OpenAI

from pocker_agent.llm import OpenAICompatibleClient


def client_for(monkeypatch, handler):
    adapter = OpenAICompatibleClient(
        "test-key", "custom-model", "https://relay.test/v1"
    )
    monkeypatch.setattr(
        adapter,
        "_sdk",
        lambda: OpenAI(
            api_key=adapter.api_key,
            base_url=adapter.base_url,
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        ),
    )
    return adapter


def test_sdk_sends_selected_model_bearer_and_json_contract(monkeypatch):
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "custom-model"
        assert "temperature" not in body
        assert body["response_format"] == {"type": "json_object"}
        return httpx2.Response(
            200, json={"choices": [{"message": {"content": '{"ok":true}'}}]}
        )

    client = client_for(monkeypatch, handler)
    assert (
        client.complete(
            [{"role": "user", "content": "json please"}],
            response_format={"type": "json_object"},
        )
        == '{"ok":true}'
    )


@pytest.mark.parametrize(
    "body",
    [
        {"data": [{"id": "z"}, {"id": "a"}, {"id": "z"}]},
        {"models": ["z", {"name": "a"}, {"model": "z"}]},
        ["z", "a"],
    ],
)
def test_model_lists_are_complete_and_deduplicated(monkeypatch, body):
    client = client_for(monkeypatch, lambda request: httpx2.Response(200, json=body))
    assert client.list_models() == ["a", "z"]


@pytest.mark.parametrize(
    "code,body",
    [
        (401, {"error": "invalid test-key"}),
        (400, {"error": "bad request"}),
        (200, {"error": "wrong envelope"}),
    ],
)
def test_errors_are_visible_and_key_is_redacted(monkeypatch, code, body):
    client = client_for(monkeypatch, lambda request: httpx2.Response(code, json=body))
    with pytest.raises(RuntimeError) as caught:
        client.list_models()
    assert "test-key" not in str(caught.value)


def test_html_completion_does_not_become_uncaught_500(monkeypatch):
    client = client_for(
        monkeypatch,
        lambda request: httpx2.Response(200, text="<html>not an API</html>"),
    )
    with pytest.raises(RuntimeError, match="无效响应"):
        client.complete([{"role": "user", "content": "hello"}])


def test_long_echoed_credential_is_redacted_before_error_is_shortened(monkeypatch):
    client = client_for(
        monkeypatch,
        lambda request: httpx2.Response(401, json={"error": client.api_key}),
    )
    client.api_key = "sensitive-" * 100
    with pytest.raises(RuntimeError) as caught:
        client.list_models()
    assert "sensitive" not in str(caught.value)
    assert "[REDACTED]" in str(caught.value)


@pytest.mark.parametrize("finished", [True, False])
@pytest.mark.parametrize("final_delta", [{}, None])
def test_streamed_json_requires_completion_before_use(
    monkeypatch, finished, final_delta
):
    def handler(request):
        assert json.loads(request.content)["stream"] is True
        chunks = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": '{"ok":true}'},
                        "finish_reason": None,
                    }
                ]
            }
        ]
        if finished:
            chunks.append(
                {
                    "choices": [
                        {"index": 0, "delta": final_delta, "finish_reason": "stop"}
                    ]
                }
            )
        data = (
            "".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
            + "data: [DONE]\n\n"
        )
        return httpx2.Response(
            200, text=data, headers={"Content-Type": "text/event-stream"}
        )

    client = client_for(monkeypatch, handler)
    client.streaming = True
    if finished:
        assert client.complete([{"role": "user", "content": "json"}]) == '{"ok":true}'
    else:
        with pytest.raises(RuntimeError, match="提前结束"):
            client.complete([{"role": "user", "content": "json"}])


@pytest.mark.parametrize("parameter", ["reasoning_effort", "max_completion_tokens"])
def test_optional_generation_parameter_fallback_preserves_model_and_messages(
    monkeypatch, parameter
):
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if parameter in body:
            return httpx2.Response(
                400, json={"error": "unsupported parameter: " + parameter}
            )
        return httpx2.Response(
            200, json={"choices": [{"message": {"content": '{"ok":true}'}}]}
        )

    client = client_for(monkeypatch, handler)
    setattr(client, parameter, "low" if parameter == "reasoning_effort" else 12000)
    notices = []
    client.on_notice = notices.append
    messages = [{"role": "user", "content": "json"}]
    assert client.complete(messages) == '{"ok":true}'
    assert len(requests) == 2 and len(notices) == 1
    assert requests[0]["messages"] == requests[1]["messages"] == messages
    assert requests[0]["model"] == requests[1]["model"] == "custom-model"


def test_stream_service_error_preserves_reason_and_redacts_key(monkeypatch):
    def handler(request):
        body = {
            "error": {
                "message": "The service is busy. test-key",
                "type": "server_error",
            }
        }
        return httpx2.Response(
            200,
            text="data: " + json.dumps(body) + "\n\n",
            headers={"Content-Type": "text/event-stream"},
        )

    client = client_for(monkeypatch, handler)
    client.streaming = True
    with pytest.raises(RuntimeError, match="service is busy") as caught:
        client.complete([{"role": "user", "content": "hello"}])
    assert "test-key" not in str(caught.value)


@pytest.mark.parametrize("needs_new_parameter", [False, True])
def test_output_limit_works_with_both_compatible_parameter_names(
    monkeypatch, needs_new_parameter
):
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        if needs_new_parameter and "max_tokens" in body:
            return httpx2.Response(
                400, json={"error": "max_tokens unsupported; use max_completion_tokens"}
            )
        name = "max_completion_tokens" if needs_new_parameter else "max_tokens"
        assert body[name] == 12000
        assert not ("max_tokens" in body and "max_completion_tokens" in body)
        return httpx2.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    client = client_for(monkeypatch, handler)
    client.max_tokens = 12000
    assert client.complete([{"role": "user", "content": "hello"}]) == "OK"
    assert len(bodies) == (2 if needs_new_parameter else 1)
