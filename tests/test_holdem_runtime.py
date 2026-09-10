from fastapi.testclient import TestClient
from pocker_agent.api import create_app
from pocker_agent.game_rules import HoldemRule

def test_holdem_runtime_can_create_and_restore(tmp_path):
    r = HoldemRule(schema_version="0.2",game_id="holdem",title="德州",deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},players={"min_players":2,"max_players":2,"starting_hand_size":2},max_rounds=1,kind="holdem")
    c = TestClient(create_app(tmp_path / "h.db")); x = c.post("/api/runtime/sessions",json=r.model_dump(mode="json"))
    assert x.status_code == 200; body=x.json(); assert body["pot"] == 30
    assert c.get("/api/runtime/sessions/"+body["session_id"]).status_code == 200


def test_holdem_runtime_uses_declared_tool_plan_for_live_actions(tmp_path):
    r = HoldemRule(schema_version="0.2",game_id="holdem-plan",title="德州",deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},players={"min_players":2,"max_players":2,"starting_hand_size":2},max_rounds=1,kind="holdem")
    plan = {"game_kind":"holdem", "players":2,
            "tools":[{"name":"deck", "config":{"ranks":r.deck.ranks,"suits":r.deck.suits}}, {"name":"zones"}],
            "actions":[]}
    c = TestClient(create_app(tmp_path / "h-plan.db")); x = c.post("/api/runtime/sessions?seed=7",json={"rules":r.model_dump(mode="json"), "tool_plan":plan})
    assert x.status_code == 200
    state = x.json()
    # The generated plan is the allow-list for the live runtime.  A missing
    # betting_round tool must reject the first action instead of silently
    # switching to a host-owned betting implementation.
    rejected = c.post(f"/api/runtime/sessions/{state['session_id']}/actions/call", json={"revision":state["revision"]})
    assert rejected.status_code == 422 and "tool_not_declared:betting_round" in rejected.json()["detail"]
