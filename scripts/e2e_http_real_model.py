"""Full flow over real HTTP with a real OpenAI-compatible model.

Prereqs: backend running at 8765 with POCKER_AGENT_* env pointing to a real
model endpoint (Key stays in the backend process), frontend not required.

jobs -> confirm -> simulations -> runtime session -> actions -> restore.
Retries the whole flow (up to 4) because real-model ToolPlan output is
occasionally invalid; a user would resend in the same situation."""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error

BACKEND = "http://127.0.0.1:8765"
DESC = ("创建两人疯狂八游戏：标准52张牌无王，一名人类一名电脑，每人5张。只玩1局，"
        "同花色或同点数接牌，8为万能牌且打出时指定花色，起始牌不是8。有合法牌必须出，"
        "无合法牌持续摸到可出，牌堆耗尽回收弃牌保留顶牌，全员卡住平局，先出完获胜，"
        "隐藏对手手牌。规则已完整请直接生成。")


def api(path: str, body: dict | None = None, method: str = "GET"):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BACKEND + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {detail}")


def dump(label: str, obj) -> None:
    print(f"### {label}")
    print(json.dumps(obj, ensure_ascii=False, indent=1)[:1200])


for attempt in range(1, 5):
    print(f"=== attempt {attempt} ===")
    try:
        job = api("/api/agent/jobs", {"message": DESC}, "POST")
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            time.sleep(3)
            state = api("/api/agent/jobs/" + job["id"])
            if state["status"] != "running":
                break
        if state["status"] != "completed" or not state["result"]:
            print("JOB FAILED:", state.get("error") or state["status"])
            continue
        r = state["result"]
        print("job kind:", r["kind"], "tool_plan_source:", r.get("tool_plan_source"))
        rules, tool_plan = r["rules"], r.get("tool_plan")
        if not rules or not tool_plan:
            print("missing rules/tool_plan; retrying")
            continue

        confirm = api("/api/agent/confirm", {"proposal": rules, "tool_plan": tool_plan}, "POST")
        dump("CONFIRM", {"kind": confirm["kind"], "errors": confirm["errors"]})
        if confirm["kind"] != "confirmed":
            continue

        sim = api("/api/simulations?seed=7", rules, "POST")
        print(f"SIMULATION: completed={sim['completed']} winner={sim['winner']} events={len(sim['events'])}")

        sess = api("/api/runtime/sessions?seed=7", {"rules": rules, "tool_plan": tool_plan}, "POST")
        sid = sess["session_id"]
        print(f"SESSION: {sid} legal={sess.get('legal_actions')}")
        moves = 0
        while not sess["finished"] and moves < 60:
            acts = sess.get("legal_actions") or []
            rev = sess["revision"]
            if "play" in acts:
                idx = (sess.get("legal_card_indices") or [0])[0]
                sess = api(f"/api/runtime/sessions/{sid}/actions/play",
                           {"revision": rev, "card_index": idx, "declared_suit": "S"}, "POST")["state"]
            elif "draw" in acts:
                sess = api(f"/api/runtime/sessions/{sid}/actions/draw",
                           {"revision": rev, "card_index": 0}, "POST")["state"]
            else:
                print("NO LEGAL ACTION, state:", json.dumps(sess, ensure_ascii=False)[:400])
                break
            moves += 1
        print(f"GAME END: moves={moves} finished={sess['finished']} winners={sess.get('winners')} "
              f"reason={sess.get('finish_reason')} events={len(sess['events'])}")
        if not sess["finished"]:
            print("game not finished; retrying")
            continue

        restored = api(f"/api/runtime/sessions/{sid}")
        print(f"RESTORE: finished={restored['finished']} winners={restored.get('winners')} revision={restored.get('revision')}")
        print("=== HTTP E2E PASSED (attempt %d) ===" % attempt)
        break
    except Exception as e:
        print("flow error:", e)
        continue
else:
    print("=== HTTP E2E FAILED after 4 attempts ===")
    raise SystemExit(1)
