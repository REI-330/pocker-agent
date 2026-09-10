"""Prove the model -> Agent -> ToolPlan -> GameLayer chain over real HTTP.

The model endpoint in this check is a local OpenAI-compatible HTTP server.  It
is deliberately deterministic so the check is repeatable and does not need a
real credential.  The Pocker API still uses its production
``OpenAICompatibleClient`` and the real FastAPI endpoints; no RuleAgent or
ToolPlan internals are monkeypatched.

The generated trace is written to ``artifacts/agent-tool-chain-http.json``.
It records the model request, the model-produced rule values, the returned
plan, and the ``tool_called`` events emitted by the RuleExecutor.  This makes
it possible to tell apart a model-generated proposal from a runtime that only
started a hard-coded game engine.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

from pocker_agent.api import create_app


RULES = {
    "schema_version": "0.2",
    "game_id": "agent-http-crazy-eights",
    "title": "模型生成的疯狂八",
    "deck": {
        "suits": ["S", "H", "D", "C"],
        "ranks": ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"],
    },
    "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 5},
    "max_rounds": 1,
    "kind": "shedding",
    "match": "suit_or_rank",
    "wild_rank": "8",
    "draw_policy": "until_playable",
    "recycle_discard": True,
    "blocked_result": "draw",
}


class _Vault:
    def __init__(self):
        self.values = {}

    def set_password(self, service, user, value):
        self.values[service, user] = value

    def get_password(self, service, user):
        return self.values.get((service, user))

    def delete_password(self, service, user):
        self.values.pop((service, user), None)


class _ModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self):  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length))
        self.__class__.requests.append(body)
        # The first model call is the intent/rule Agent.  The second is the
        # game-engine Agent.  Returning a deliberately small plan lets the
        # assertions prove that the runtime executed the model's plan rather
        # than a host-side plan_for_rules fallback.
        if len(self.__class__.requests) == 1:
            payload = {"type": "proposal", "summary": "由模型返回", "rules": RULES}
        else:
            payload = {
                "tool_plan": {
                    "schema_version": "1.0",
                    "game_kind": "shedding",
                    "players": 2,
                    "tools": [
                        {"name": "deck", "config": {"ranks": RULES["deck"]["ranks"], "suits": RULES["deck"]["suits"]}},
                        {"name": "zones"},
                        {"name": "draw_discard"},
                        {"name": "card_match"},
                        {"name": "turn_order", "config": {"players": ["player-1", "player-2"]}},
                    ],
                    "actions": [
                        {"tool": "deck", "operation": "deal", "args": {"seed": 0, "hands": 2, "cards_each": 5, "kitty": 1}, "result_key": "deal"},
                        {"tool": "zones", "operation": "create", "args": {"name": "stock", "cards": "$state.deal.deck"}},
                        {"tool": "zones", "operation": "create", "args": {"name": "table", "cards": "$state.deal.kitty", "visible_to": ["*"]}},
                    ],
                }
            }
        response = {"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]}
        encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        return


def main() -> None:
    _ModelHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ModelHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = Path(__file__).resolve().parents[1]
    artifact = root / "artifacts" / "agent-tool-chain-http.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="pocker-agent-chain-") as temp:
            os.environ.update({
                "POCKER_AGENT_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                "POCKER_AGENT_API_KEY": "local-chain-test-key",
                "POCKER_AGENT_MODEL": "chain-test-model",
            })
            app = create_app(Path(temp) / "chain.db", _Vault())
            with TestClient(app) as client:
                response = client.post("/api/agent/turn", json={
                    "message": "创建一个两人疯狂八，每人五张，8 是万能牌，摸到能出的牌为止",
                })
                response.raise_for_status()
                generated = response.json()
                assert generated["kind"] == "proposal", generated
                assert generated["rules"]["game_id"] == RULES["game_id"]
                assert generated["rules"]["title"] == RULES["title"]
                plan = generated["tool_plan"]
                assert plan and plan["game_kind"] == "shedding"
                assert generated["tool_plan_source"] == "engine_agent", generated
                assert {item["name"] for item in plan["tools"]} >= {"deck", "zones", "draw_discard", "card_match", "turn_order"}

                valid = client.post("/api/tools/plan/validate", json=plan)
                valid.raise_for_status()
                assert valid.json()["valid"] is True, valid.json()
                executed = client.post("/api/tools/plan/execute", json=plan)
                executed.raise_for_status()
                body = executed.json()
                assert body["valid"] is True, body
                events = body["result"]["events"]
                called = [(event["tool"], event["operation"]) for event in events if event["event"] == "tool_called"]
                assert called == [
                    ("deck", "deal"),
                    ("zones", "create"),
                    ("zones", "create"),
                ], called
                runtime = client.post("/api/runtime/sessions?seed=7", json={"rules": generated["rules"], "tool_plan": plan})
                runtime.raise_for_status()
                runtime_state = runtime.json()
                assert runtime_state["tool_plan"] == plan
                runtime_called = [(event["tool"], event["operation"])
                                  for event in runtime_state["tool_events"]
                                  if event["event"] == "tool_called"]
                assert runtime_called == [("deck", "shuffled"), ("deck", "deal_into")], runtime_called
                assert runtime_state["tool_plan_source"] == "engine_agent"

                trace = {
                    "model_endpoint": f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                    "model": "chain-test-model",
                    "user_message": "创建一个两人疯狂八，每人五张，8 是万能牌，摸到能出的牌为止",
                    "model_requests": [{
                        "model": item.get("model"),
                        "messages": item.get("messages"),
                    } for item in _ModelHandler.requests],
                    "model_response_rules": generated["rules"],
                    "tool_plan": plan,
                    "tool_called": [{"tool": name, "operation": operation} for name, operation in called],
                    "execution_state_keys": sorted(body["result"]["state"]),
                    "runtime_tool_plan_matches": runtime_state["tool_plan"] == plan,
                    "runtime_tool_called": [{"tool": name, "operation": operation}
                                             for name, operation in runtime_called],
                }
                artifact.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({
                    "model_requests": len(_ModelHandler.requests),
                    "generated_game_id": generated["rules"]["game_id"],
                    "plan_tools": [item["name"] for item in plan["tools"]],
                    "tool_plan_source": generated["tool_plan_source"],
                    "tool_called": trace["tool_called"],
                    "artifact": str(artifact),
                }, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
