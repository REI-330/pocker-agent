"""Real source-server proof of model -> ToolPlan -> Hold'em tools.

The model endpoint is a deterministic local OpenAI-compatible HTTP service;
the Pocker API itself runs in a separate source checkout Uvicorn process.
The script then plays one hand through the public runtime endpoints and
asserts that every street is represented by a declared tool call.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RANKS = ["A", *map(str, range(2, 11)), "J", "Q", "K"]
RULES = {
    "schema_version": "0.2", "game_id": "agent-http-holdem", "title": "模型生成德州",
    "kind": "holdem", "max_rounds": 1,
    "deck": {"suits": ["S", "H", "D", "C"], "ranks": RANKS},
    "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 2},
    "starting_chips": 100, "small_blind": 5, "big_blind": 10,
    "streets": ["preflop", "flop", "turn", "river"],
    "actions": ["fold", "check", "call", "raise", "all_in"],
    "dealing": "two_private_and_community",
}


def holdem_plan():
    # Keep this fixture aligned with the host's declarative composition path.
    # The model response is still the source of the plan; the helper only
    # supplies a deterministic valid ToolPlan for the local fake model.
    from pocker_agent.game_rules import HoldemRule
    from pocker_agent.tools.plans import plan_for_rules
    return plan_for_rules(HoldemRule.model_validate(RULES))
    """
    tools = [
        {"name": "deck", "config": {"ranks": RANKS, "suits": ["S", "H", "D", "C"]}},
        {"name": "zones"}, {"name": "pot", "config": {"stacks": [100, 100]}},
        {"name": "betting_round", "config": {"stacks": [100, 100], "min_raise": 10}},
        {"name": "phase_progress", "config": {"phases": RULES["streets"]}},
        {"name": "community_deal"}, {"name": "all_in"}, {"name": "showdown"},
        {"name": "settle_pots"}, {"name": "hand_rank", "config": {"best_of": 7}},
    ]
    return {"schema_version": "1.0", "game_kind": "holdem", "players": 2,
            "tools": tools, "phases": RULES["streets"], "requirements": [],
            "actions": [{"tool": "deck", "operation": "deal",
                          "args": {"seed": 0, "hands": 2, "cards_each": 2}, "result_key": "deal"}],
            "end_conditions": ["phase_progress.finished", "all_in.runout_required", "showdown.completed"]}
    """


class ModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", "0"))))
        self.__class__.requests.append(body)
        payload = ({"type": "proposal", "summary": "由模型返回", "rules": RULES}
                   if len(self.__class__.requests) == 1 else {"tool_plan": holdem_plan()})
        encoded = json.dumps({"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]}).encode()
        self.send_response(200); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)

    def log_message(self, *_args):
        return


def main():
    ModelHandler.requests = []
    model = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    data = Path(tempfile.mkdtemp(prefix="holdem-agent-", dir=ROOT / ".validation"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-m", "uvicorn", "pocker_agent.api:app", "--host", "127.0.0.1", "--port", str(port)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), POCKER_AGENT_DATA_DIR=str(data),
               POCKER_AGENT_BASE_URL=f"http://127.0.0.1:{model.server_port}/v1",
               POCKER_AGENT_API_KEY="local-holdem-test", POCKER_AGENT_MODEL="holdem-chain-model")
    log = (data / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def request(path, body=None, expected=200):
        req = Request(base + path, data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=20) as response:
                assert response.status == expected, response.status
                return json.load(response)
        except HTTPError as error:
            if error.code != expected:
                detail = error.read().decode("utf-8", "replace")
                raise RuntimeError(f"HTTP {error.code}: {detail}") from error
            return json.load(error)

    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if request("/health")["status"] == "ok": break
            except (URLError, OSError):
                time.sleep(0.1)
        generated = request("/api/agent/turn", {"message": "创建一个两人德州扑克，起始筹码100，小盲5大盲10"})
        assert generated["tool_plan_source"] == "engine_agent", generated
        plan = generated["tool_plan"]
        assert plan["game_kind"] == "holdem"
        state = request("/api/runtime/sessions?seed=7", {"rules": generated["rules"], "tool_plan": plan})
        sid, path = state["session_id"], None
        path = f"/api/runtime/sessions/{sid}"
        calls = {(e["tool"], e["operation"]) for e in state["tool_events"] if e["event"] == "tool_called"}
        actions = ["call", "check", "call", "check", "check", "check", "check", "check"]
        for action in actions:
            print("playing", action, state.get("current_player"), state.get("legal_actions"), state.get("street"))
            result = request(path + f"/actions/{action}", {"revision": state["revision"]})
            calls.update((e["tool"], e["operation"]) for e in result["events"] if e["event"] == "tool_called")
            state = result["state"]
            print(" ->", state.get("flow_node"), state.get("current_player"), state.get("legal_actions"), state.get("street"))
        assert state["finished"] and len(state["board"]) == 5, state
        required = {("betting_round", "act"), ("all_in", "check"),
                    ("phase_progress", "advance"), ("community_deal", "deal"),
                    ("showdown", "call"), ("settle_pots", "call")}
        assert required <= calls, sorted(calls)
        artifact = ROOT / "artifacts" / "holdem-agent-runtime-http.json"
        artifact.parent.mkdir(exist_ok=True)
        artifact.write_text(json.dumps({"startup": command, "checkout": str(ROOT),
            "model_requests": len(ModelHandler.requests), "tool_plan": plan,
            "tool_plan_source": generated["tool_plan_source"], "actions": actions,
            "finished": state["finished"], "board_count": len(state["board"]),
            "tool_called": sorted([{"tool": a, "operation": b} for a, b in calls], key=lambda x: (x["tool"], x["operation"]))}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"model_requests": len(ModelHandler.requests), "tool_plan_source": generated["tool_plan_source"],
                          "actions": actions, "finished": state["finished"], "board_count": len(state["board"]),
                          "tool_called": sorted(calls), "artifact": str(artifact)}, ensure_ascii=False))
    finally:
        process.terminate(); process.wait(timeout=10); log.close(); model.shutdown(); model.server_close()


if __name__ == "__main__":
    main()
