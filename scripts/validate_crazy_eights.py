"""Real HTTP/lifecycle smoke: source uvicorn, SQLite restart, legal play to end.

Run with the checkout virtualenv Python. No API key or model call is required;
this validates the gameplay after a rule has been generated and confirmed.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / ".validation"
    folder.mkdir(exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="crazy-eights-", dir=folder))
    with socket.socket() as socket_:
        socket_.bind(("127.0.0.1", 0))
        port = socket_.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-m", "uvicorn", "pocker_agent.api:app", "--host", "127.0.0.1", "--port", str(port)]
    env = dict(os.environ, POCKER_AGENT_DATA_DIR=str(data), PYTHONPATH=str(ROOT / "src"))
    process = None
    log = (data / "server.log").open("w", encoding="utf-8")

    def request(path, body=None, expected=200):
        req = Request(base + path, data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=20) as response:
                assert response.status == expected, response.status
                return json.load(response)
        except HTTPError as error:
            assert error.code == expected, f"{path}: HTTP {error.code}"
            return json.load(error)

    def stop():
        nonlocal process
        if process is not None:
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
                raise RuntimeError(f"Source server exited; inspect {data / 'server.log'}")
            try:
                if request("/health")["status"] == "ok": return
            except (URLError, OSError):
                time.sleep(0.1)
        raise RuntimeError("source_start_timeout")

    records = []
    try:
        start()
        for players in (2, 3, 4):
            rule = {
                "schema_version": "0.2", "kind": "shedding", "game_id": f"crazy-{players}",
                "title": "Crazy Eights verification", "max_rounds": 1,
                "deck": {"suits": ["S", "H", "D", "C"], "ranks": ["A", *map(str, range(2, 11)), "J", "Q", "K"]},
                "players": {"min_players": players, "max_players": players, "starting_hand_size": 5},
                "match": "suit_or_rank", "wild_rank": "8", "draw_policy": "until_playable",
                "recycle_discard": True, "blocked_result": "draw",
            }
            assert request("/api/agent/confirm", {"proposal": rule})["kind"] == "confirmed"
            state = request("/api/runtime/sessions?seed=3", rule)
            sid = state["session_id"]
            path = "/api/runtime/sessions/" + sid
            assert len(state["players"]) == players
            restarted = False
            actions = []
            calls = set()
            for step in range(500):
                if state["finished"]: break
                assert state["current_player"] == "player-1"
                assert "seed" not in state
                assert all(p["hand"] == [] for p in state["players"][1:])
                hand, top = state["players"][0]["hand"], state["table"][-1]
                # Independent rules predicate, deliberately not importing Tool code.
                legal = [i for i, card in enumerate(hand) if card["rank"] == "8"
                         or card["rank"] == top["rank"] or card["suit"] == state["active_suit"]]
                assert legal == state["legal_card_indices"]
                action = "play" if legal else state["legal_actions"][0]
                index = next((i for i in legal if hand[i]["rank"] == "8"), legal[0] if legal else 0)
                revision = state["revision"]
                args = {"revision": revision, "card_index": index, "declared_suit": "C"}
                if action == "play" and hand[index]["rank"] == "8":
                    request(path + "/actions/play", {**args, "declared_suit": ""}, expected=422)
                    assert request(path) == state
                result = request(path + "/actions/" + action, args)
                actions.append(action)
                calls.update((e["tool"], e["operation"]) for e in result["events"] if e["event"] == "tool_called")
                state = result["state"]
                assert state["revision"] == revision + 1
                request(path + "/actions/" + action, args, expected=409)
                assert request(path) == state
                if not restarted:
                    stop()
                    start()
                    assert request(path) == state
                    restarted = True
            assert state["finished"] and state["winners"]
            assert restarted and ("draw_discard", "discard_cards") in calls
            records.append({"players": players, "seed": 3, "human_actions": len(actions),
                            "actions": sorted(set(actions)), "tool_calls": sorted(calls),
                            "reason": state["finish_reason"], "winners": state["winners"],
                            "restart_restored": restarted})
            print(json.dumps(records[-1], ensure_ascii=False), flush=True)
    finally:
        stop()
        log.close()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    import pocker_agent
    output = {"head": revision, "dirty_checkout": True, "checkout": str(ROOT),
              "package_source": pocker_agent.__file__, "startup": command,
              "database": str(data / "pocker.db"), "scenarios": records}
    destination = ROOT / "artifacts" / "crazy-eights-http.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(destination), flush=True)


if __name__ == "__main__":
    main()
