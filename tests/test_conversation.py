import json
import threading
import time

from pocker_agent.conversation import ConversationService, ConversationStatus
from pocker_agent.llm import OpenAICompatibleClient


class Model:
    def complete(self, messages, **kwargs):
        return json.dumps(
            {"type": "question", "question": "需要几名玩家？", "missing": ["players"]}
        )


class RecordingModel(Model):
    def __init__(self):
        self.messages = []

    def complete(self, messages, **kwargs):
        self.messages = messages
        return super().complete(messages, **kwargs)


def test_conversation_turn_is_chat_and_confirm_requires_revision():
    service = ConversationService()
    item = service.create()
    model = RecordingModel()
    result = service.turn(item.id, "做一个纸牌游戏", model, request_id="turn-1")
    assert result.kind == "question"
    assert model.messages[-1] == {"role": "user", "content": "做一个纸牌游戏"}
    assert service.get(item.id).status == ConversationStatus.DESIGNING
    assert service.get(item.id).revision == 1
    duplicate = service.turn(item.id, "做一个纸牌游戏", model, request_id="turn-1")
    assert duplicate.message == result.message
    assert len(service.get(item.id).session.messages) == 2
    try:
        service.confirm(item.id, 0)
    except ValueError as error:
        assert str(error) == "stale_conversation_revision"


def test_http_conversation_keeps_chat_separate_from_build(local_app, monkeypatch):
    _, client, _ = local_app
    client.post(
        "/api/agent/config",
        json={"base_url": "https://model.test", "api_key": "key", "model": "m"},
    )
    replies = iter(
        [
            json.dumps({"message": "需要明确人数。", "ready": False, "draft": None}),
            json.dumps(
                {
                    "message": "规则已完整，请确认。",
                    "ready": True,
                    "draft": {
                        "title": "比大小",
                        "summary": "两人各发一张牌，点数高者获胜。",
                    },
                }
            ),
        ]
    )
    monkeypatch.setattr(
        OpenAICompatibleClient, "complete", lambda self, *a, **k: next(replies)
    )
    created = client.post("/api/conversations", json={}).json()
    first = client.post(
        "/api/conversations/" + created["id"] + "/messages",
        json={"message": "做个游戏", "revision": 0, "request_id": "r1"},
    ).json()
    assert first["phase"] == "designing" and first["job"] is None
    duplicate = client.post(
        "/api/conversations/" + created["id"] + "/messages",
        json={"message": "做个游戏", "revision": 0, "request_id": "r1"},
    ).json()
    assert duplicate["revision"] == first["revision"]
    assert duplicate["messages"] == first["messages"]
    second = client.post(
        "/api/conversations/" + created["id"] + "/messages",
        json={"message": "两个人", "revision": first["revision"], "request_id": "r2"},
    ).json()
    assert second["phase"] == "proposal_ready" and second["draft"]["title"] == "比大小"


def test_cancel_does_not_hold_repository_lock_while_model_is_running():
    class BlockingModel:
        def complete(self, messages, **kwargs):
            gate.wait(2)
            return json.dumps({"message": "late", "ready": False, "draft": None})

    service = ConversationService()
    item = service.create()
    gate = threading.Event()
    result = []

    def run():
        try:
            result.append(service.turn(item.id, "开始", BlockingModel()))
        except ValueError as error:
            result.append(error)

    worker = threading.Thread(target=run)
    worker.start()
    for _ in range(20):
        if service.get(item.id).phase.value == "thinking":
            break
        time.sleep(0.01)
    started = time.monotonic()
    service.cancel(item.id, service.get(item.id).revision)
    assert time.monotonic() - started < 0.5
    gate.set()
    worker.join(2)
    assert service.get(item.id).phase.value == "designing"
    assert isinstance(result[0], ValueError)


def test_build_polling_does_not_mutate_revision_without_progress_change():
    service = ConversationService()
    item = service.create()
    service.attach_job(
        item.id,
        {
            "id": "job-1",
            "kind": "build",
            "status": "running",
            "progress": [],
            "error": None,
        },
    )
    revision = service.get(item.id).revision
    service.publish_build(
        item.id,
        {
            "id": "job-1",
            "kind": "build",
            "status": "running",
            "progress": [],
            "error": None,
        },
    )
    assert service.get(item.id).revision == revision
    service.publish_build(
        item.id,
        {
            "id": "job-1",
            "kind": "build",
            "status": "running",
            "progress": [{"message": "进行中"}],
            "error": None,
        },
    )
    assert service.get(item.id).revision == revision + 1


def test_new_design_turn_invalidates_previous_game_artifacts():
    service = ConversationService()
    item = service.create()
    item.draft = {"title": "旧游戏", "summary": "旧规则"}
    item.session.proposal = {
        "title": "旧游戏",
        "description": "旧规则",
        "schema_version": "0.1",
    }
    item.job = {"id": "old", "status": "completed"}
    item.runtime_id = "runtime-old"
    model = Model()
    service.turn(item.id, "修改规则", model)
    current = service.get(item.id)
    assert current.session.proposal is None
    assert current.job is None
    assert current.runtime_id is None
    assert current.phase == ConversationStatus.DESIGNING


def test_cancel_build_returns_to_confirmation_state_when_draft_exists():
    service = ConversationService()
    item = service.create()
    item.draft = {"title": "游戏", "summary": "规则"}
    item.phase = ConversationStatus.BUILDING
    item.revision = 4
    cancelled = service.cancel(item.id, 4)
    assert cancelled.phase == ConversationStatus.PROPOSAL_READY
