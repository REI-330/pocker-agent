from pocker_agent.executors import create_engine
from pocker_agent.game_rules import DoudizhuRule
from pocker_agent.api import create_app
from fastapi.testclient import TestClient


def rule():
    return DoudizhuRule(schema_version="0.2", game_id="ddz", title="斗地主",
        deck={"suits":["S","H","D","C"],"ranks":["3","4","5","6","7","8","9","10","J","Q","K","A","2","BJ","RJ"]},
        players={"min_players":3,"max_players":3,"starting_hand_size":17}, max_rounds=1, kind="doudizhu")


def test_doudizhu_deal_and_bidding_are_deterministic():
    first = create_engine(rule(), seed=4); first.setup()
    second = create_engine(rule(), seed=4); second.setup()
    assert [c.id for c in first.state.hands[0]] == [c.id for c in second.state.hands[0]]
    assert sum(map(len, first.state.hands)) == 51 and len(first.state.kitty) == 3
    first.step("bid:3")
    assert first.state.landlord == 0 and len(first.state.hands[0]) == 20
    assert first.view()["kind"] == "doudizhu"


def test_doudizhu_runtime_snapshot_and_restore(tmp_path):
    client = TestClient(create_app(tmp_path / "runtime.db"))
    response = client.post("/api/runtime/sessions", json=rule().model_dump(mode="json"))
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "doudizhu" and body["kitty"] == []
    restored = client.get("/api/runtime/sessions/" + body["session_id"])
    assert restored.status_code == 200 and restored.json()["session_id"] == body["session_id"]


def test_doudizhu_engine_exposes_multi_card_actions():
    engine = create_engine(rule(), seed=2); engine.setup(); engine.step("bid:3")
    actions = engine.legal_actions()
    assert any(a.startswith("play:") and "," in a for a in actions)
