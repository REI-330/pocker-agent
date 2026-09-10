"""Verify that live family actions are constrained by the Agent ToolPlan."""


from fastapi.testclient import TestClient

from pocker_agent.api import create_app
from pocker_agent.runtime import RuntimeStore
from pocker_agent.game_rules import parse_rule
from pocker_agent.tools.plans import plan_for_rules


def _blackjack_rules():
    return {
        "schema_version": "0.2", "kind": "blackjack", "game_id": "plan-blackjack",
        "title": "计划约束21点", "max_rounds": 1,
        "deck": {"suits": ["S", "H", "D", "C"], "ranks": ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]},
        "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 2},
        "target": 21, "dealer_stand_on": 17, "dealer_hits_soft_17": False,
        "natural_beats_21": True, "betting": False, "dealing": "fresh_deck_each_round",
    }


def test_blackjack_startup_cannot_skip_declared_hand_rank(tmp_path):
    rules = _blackjack_rules()
    plan = {"game_kind": "blackjack", "players": 2,
            "tools": [{"name": "deck", "config": {"ranks": rules["deck"]["ranks"], "suits": rules["deck"]["suits"]}}]}
    client = TestClient(create_app(tmp_path / "plan.db"))
    response = client.post("/api/runtime/sessions?seed=7", json={"rules": rules, "tool_plan": plan})
    assert response.status_code == 422
    assert "tool_not_declared:hand_rank" in response.json()["detail"]


def test_blackjack_rejects_plan_value_rule_mismatch(tmp_path):
    rules = _blackjack_rules()
    plan = {"game_kind": "blackjack", "players": 2,
            "tools": [{"name": "deck", "config": rules["deck"]},
                      {"name": "hand_rank", "config": {"target": 17}}]}
    client = TestClient(create_app(tmp_path / "mismatch.db"))
    response = client.post("/api/runtime/sessions?seed=7", json={"rules": rules, "tool_plan": plan})
    assert response.status_code == 422
    assert "tool_plan_config_mismatch:hand_rank.target" in response.json()["detail"]


def test_plan_provenance_requires_server_generation_record_and_survives_restart(tmp_path):
    rules = parse_rule(_blackjack_rules())
    plan = plan_for_rules(rules)
    path = tmp_path / "provenance.db"
    store = RuntimeStore(path)
    assert store.create(rules, seed=7, tool_plan=plan).tool_plan_source == "provided_plan"
    store.register_generated_plan(rules, plan, "engine_agent")
    generated = store.create(rules, seed=7, tool_plan=plan)
    assert RuntimeStore(path).get(generated.id).tool_plan_source == "engine_agent"
    altered = {**plan, "requirements": ["client_modified"]}
    assert store.create(rules, seed=7, tool_plan=altered).tool_plan_source == "provided_plan"


