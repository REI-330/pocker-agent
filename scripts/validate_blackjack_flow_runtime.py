"""Source-server smoke test for an engine-free, declarative Blackjack flow."""
import json, subprocess, sys, time
from urllib.request import Request, urlopen
from pocker_agent.game_rules import BlackjackRule
from pocker_agent.tools.plans import plan_for_rules

BASE = "http://127.0.0.1:8891"

def request(path, payload=None):
    req = Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
    with urlopen(req, timeout=15) as response:
        return json.loads(response.read())

def main():
    rules = BlackjackRule(schema_version="0.2", game_id="flow-blackjack", title="Flow Blackjack",
        deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},
        players={"min_players":2,"max_players":2,"starting_hand_size":2}, max_rounds=1, kind="blackjack",
        target=21, dealer_stand_on=17, dealer_hits_soft_17=False, natural_beats_21=True,
        dealing="fresh_deck_each_round", betting=False)
    plan = plan_for_rules(rules)
    if "flow" not in plan: raise RuntimeError("blackjack_flow_missing")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "pocker_agent.api:app", "--host", "127.0.0.1", "--port", "8891"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                if urlopen(BASE + "/health", timeout=1).status == 200: break
            except Exception: time.sleep(.1)
        else: raise RuntimeError("source_server_not_ready")
        state = request("/api/runtime/sessions", {"rules": rules.model_dump(mode="json"), "tool_plan": plan},)
        if state.get("execution_mode") != "tool_flow": raise RuntimeError(state)
        session_id, revision = state["session_id"], state["revision"]
        result = request(f"/api/runtime/sessions/{session_id}/actions/hit", {"revision": revision})
        after = result["state"]
        restored = request(f"/api/runtime/sessions/{session_id}")
        print(json.dumps({"execution_mode": after["execution_mode"], "finished": after["finished"],
                          "restored_node": restored["flow_node"], "tool_events": after["tool_events"]}, ensure_ascii=False))
    finally: proc.terminate(); proc.wait(timeout=10)

if __name__ == "__main__": main()
