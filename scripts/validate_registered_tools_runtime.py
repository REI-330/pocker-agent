"""Source Uvicorn + saved external model + persisted ToolPlans + playable rounds.

No model stub is used. Credentials are read from ConfigStore and passed only
in the child environment. The output records the provider and code identity,
never the key. Run: uv run python scripts/validate_registered_tools_runtime.py
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pocker_agent.configuration import ConfigStore

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {
    "blackjack": "创建二十一点练习，标准52张无王，2人包含电脑庄家，各2张；只玩1轮，不下注不分牌不加倍无保险。A=1或11，JQK=10，目标21，庄家不足17要牌，软17停牌，两张21优先。每轮新牌堆，玩家爆牌立即输，平局不加分，胜者1分。规则已完整请直接生成。",
    "shedding": "创建3人疯狂八，一名人类两个电脑，每人5张，标准52张牌无王。只玩1局，同花色或同点数接牌，8为万能牌且打出指定花色，起始牌不是8。有合法牌必须出，无合法牌持续摸到可出，牌堆耗尽回收弃牌保留顶牌，全员卡住平局，先出完获胜，隐藏对手手牌。规则已完整请直接生成。",
    "arithmetic": "生成24点练习，仅1人1题，标准52张无王，A=1，2到10按面值，J=11 Q=12 K=13。每题4张牌各使用恰好一次，允许加减乘除和括号，允许中间分数，目标24，只出有解题，每题重新洗牌，答对1分。规则已完整请直接生成。",
}


def expression_for(numbers):
    """Independent exact expression enumeration; does not import the game solver."""
    def search(items):
        if len(items) == 1:
            return items[0][1] if items[0][0] == 24 else None
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, left = items[i]
                b, right = items[j]
                rest = [x for k, x in enumerate(items) if k not in (i, j)]
                options = [(a + b, f"({left}+{right})"), (a * b, f"({left}*{right})"),
                           (a - b, f"({left}-{right})"), (b - a, f"({right}-{left})")]
                if b:
                    options.append((a / b, f"({left}/{right})"))
                if a:
                    options.append((b / a, f"({right}/{left})"))
                for option in options:
                    answer = search(rest + [option])
                    if answer:
                        return answer
        return None
    return search([(Fraction(n), str(n)) for n in numbers])


def main():
    config = ConfigStore().read()
    if not config.public()["configured"]:
        raise RuntimeError("saved_external_model_not_configured")
    folder = ROOT / ".validation"
    folder.mkdir(exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="registered-tools-", dir=folder))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-m", "uvicorn", "pocker_agent.api:app",
               "--host", "127.0.0.1", "--port", str(port)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), POCKER_AGENT_DATA_DIR=str(data),
               POCKER_AGENT_BASE_URL=config.base_url, POCKER_AGENT_MODEL=config.model,
               POCKER_AGENT_API_KEY=config.api_key, PYTHONIOENCODING="utf-8")
    log = (data / "server.log").open("w", encoding="utf-8")
    process = None

    def request(path, body=None, expected=200):
        req = Request(base + path, None if body is None else json.dumps(body).encode(),
                      {"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=30) as response:
                assert response.status == expected
                return json.load(response)
        except HTTPError as error:
            detail = json.load(error)
            if error.code != expected:
                raise RuntimeError(f"{path}: {error.code}: {detail}") from None
            return detail

    def stop():
        nonlocal process
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            process = None

    def start():
        nonlocal process
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("source_server_exited")
            try:
                if request("/health")["status"] == "ok":
                    return
            except (OSError, URLError):
                time.sleep(0.1)
        raise RuntimeError("source_start_timeout")

    import pocker_agent
    evidence = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "checkout": str(ROOT), "package_source": pocker_agent.__file__, "startup": command,
                "source_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "src").rglob("*.py")))).hexdigest(),
                "provider": config.base_url, "model": config.model, "model_fixture": False,
                "database": str(data / "pocker.db"), "scenarios": []}
    artifact = ROOT / "artifacts" / "registered-tools-external-http.json"
    artifact.parent.mkdir(exist_ok=True)
    try:
        start()
        selected = os.getenv("POCKER_AGENT_SCENARIO")
        scenarios = {selected: PROMPTS[selected]} if selected else PROMPTS
        for kind, prompt in scenarios.items():
            print(json.dumps({"stage": "external_generation", "kind": kind}), flush=True)
            job = request("/api/agent/jobs", {"message": prompt})
            deadline = time.monotonic() + 450
            while time.monotonic() < deadline:
                job = request("/api/agent/jobs/" + job["id"])
                if job["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.5)
            if job["status"] != "completed":
                raise RuntimeError(f"external_generation_failed:{kind}:{job}")
            generated = job["result"]
            assert generated["kind"] == "proposal", generated
            rules, plan = generated["rules"], generated["tool_plan"]
            assert rules["kind"] == kind
            assert generated["tool_plan_source"] in {"engine_agent", "engine_agent_normalized"}
            confirm = request("/api/agent/confirm", {"proposal": rules, "tool_plan": plan})
            assert confirm["kind"] == "confirmed", confirm
            state = request("/api/runtime/sessions?seed=7", {"rules": rules, "tool_plan": plan})
            path = "/api/runtime/sessions/" + state["session_id"]
            assert state["tool_plan"] == plan
            assert state["tool_plan_source"] == generated["tool_plan_source"]
            stop()
            start()
            assert request(path) == state  # SQLite restore includes provenance
            actions = []
            for _ in range(400):
                if state["finished"]:
                    break
                args = {"revision": state["revision"]}
                if kind == "blackjack":
                    action = "stand"
                elif kind == "arithmetic":
                    action = "submit_expression"
                    args["expression"] = expression_for(state["numbers"])
                    assert args["expression"] is not None
                else:
                    hand, top = state["players"][0]["hand"], state["table"][-1]
                    choices = [i for i, c in enumerate(hand) if c["rank"] == "8"
                               or c["rank"] == top["rank"] or c["suit"] == state["active_suit"]]
                    assert choices == state["legal_card_indices"]
                    assert all(not p["hand"] for p in state["players"][1:])
                    action = "play" if choices else state["legal_actions"][0]
                    args.update(card_index=choices[0] if choices else 0, declared_suit="C")
                result = request(path + "/actions/" + action, args)
                state = result["state"]
                actions.append(action)
                assert state["revision"] == args["revision"] + 1
                request(path + "/actions/" + action, args, expected=409)
                assert request(path) == state
            assert state["finished"], "game_did_not_finish"
            calls = sorted({(e["tool"], e["operation"]) for e in state["tool_events"]})
            expected = {"blackjack": {("hand_rank", "evaluate"), ("deck", "deal_into")},
                        "shedding": {("card_match", "call"), ("draw_discard", "discard_cards"), ("turn_order", "advance")},
                        "arithmetic": {("arithmetic_solver", "validate"), ("deck", "draw")}}[kind]
            assert expected <= set(calls), calls
            if kind == "arithmetic":
                assert state["players"][0]["score"] == 1
            record = {"kind": kind, "rules": rules, "plan": plan, "source": state["tool_plan_source"],
                      "actions": actions, "tool_calls": calls, "finished": True,
                      "restart_restored": True, "revision_conflicts_rejected": True}
            evidence["scenarios"].append(record)
            artifact.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"kind": kind, "finished": True, "actions": len(actions), "tool_calls": calls}), flush=True)
    finally:
        stop()
        log.close()
    print(str(artifact), flush=True)


if __name__ == "__main__":
    main()
