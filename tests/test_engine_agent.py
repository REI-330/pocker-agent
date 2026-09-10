import json
import pytest

from pocker_agent.engine_agent import EngineAgent
from pocker_agent.game_rules import HoldemRule
from pocker_agent.tools.plans import plan_for_rules


class FakeModel:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, messages, *, response_format=None):
        self.calls.append(messages)
        return self.response


def holdem_rule():
    return HoldemRule(
        schema_version="0.2", game_id="engine-agent-test", title="德州",
        deck={"suits": ["S", "H", "D", "C"], "ranks": ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]},
        players={"min_players": 2, "max_players": 2, "starting_hand_size": 2},
        max_rounds=1, kind="holdem",
    )


def test_engine_agent_returns_model_plan_and_provenance():
    expected = plan_for_rules(holdem_rule())
    expected["actions"] = []
    response = {"tool_plan": expected}
    model = FakeModel(json.dumps(response))
    plan, source = EngineAgent(model).compose(holdem_rule())
    assert source == "engine_agent"
    assert plan["game_kind"] == "holdem"
    assert plan["tools"] == [{"name": item["name"], "config": item.get("config", {})}
                             for item in expected["tools"]]
    assert plan["actions"] == []
    assert len(model.calls) == 1
    assert "ToolPlan" in model.calls[0][1]["content"]


def test_engine_agent_rejects_invalid_family_plan_instead_of_fabricating_one():
    model = FakeModel("not json")
    with pytest.raises(ValueError, match="engine_agent_invalid_tool_plan"):
        EngineAgent(model).compose(holdem_rule())
    assert len(model.calls) == 2


def test_engine_agent_lowers_gateway_phase_plan_without_executing_gateway_code():
    expected = plan_for_rules(holdem_rule())
    model = FakeModel(json.dumps({"game_kind": "holdem", "players": {"min_players": 2, "max_players": 2},
        "tools": expected["tools"],
        "phases": [{"name": "preflop"}, {"name": "flop"}],
        "end_conditions": [{"condition": "round_completed"}]}))
    plan, source = EngineAgent(model).compose(holdem_rule())
    assert source == "engine_agent_normalized"
    assert plan["game_kind"] == "holdem" and plan["players"] == 2
    assert all(isinstance(item["name"], str) for item in plan["tools"])
    assert plan["actions"] == []  # no host-generated initialization inserted


def test_incomplete_gateway_plan_is_not_completed_by_host():
    model = FakeModel(json.dumps({"game_kind": "holdem", "players": {"max_players": 2},
                                 "tools": ["deck"], "phases": [{"name": "preflop"}]}))
    with pytest.raises(ValueError, match="engine_agent_invalid_tool_plan"):
        EngineAgent(model).compose(holdem_rule())


def test_unknown_gateway_tool_is_not_silently_discarded():
    expected = plan_for_rules(holdem_rule())
    expected["players"] = {"max_players": 2}
    expected["tools"].append("make_up_game")
    with pytest.raises(ValueError, match="engine_agent_invalid_tool_plan"):
        EngineAgent(FakeModel(json.dumps(expected))).compose(holdem_rule())
