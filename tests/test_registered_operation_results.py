from copy import deepcopy

import pytest

from pocker_agent.tools import CardRef, DeckTool, ToolError, ToolPlan, default_registry
from pocker_agent.game_layer import GameLayer


def test_deal_into_preserves_round_robin_and_rejects_exhaustion_atomically():
    deck = DeckTool(["2", "3", "4"], ["H", "S"])
    stock, hands = deck.cards(), [[], []]
    original = deepcopy(stock)
    assert deck.deal_into(stock, hands, cards_each=2) == 4
    assert hands == [[original[-1], original[-3]], [original[-2], original[-4]]]
    before = deepcopy((stock, hands))
    with pytest.raises(ToolError, match="deck_exhausted"):
        deck.deal_into(stock, hands, cards_each=2)
    assert (stock, hands) == before


def test_registered_rank_consumes_iterable_once_and_handles_soft_aces():
    tool = default_registry().create("hand_rank", target=21)
    cards = [CardRef("AH", "A", "H", 14), CardRef("AS", "A", "S", 14), CardRef("9H", "9", "H", 9)]
    assert tool.evaluate(iter(cards)) == {"total": 21, "soft": True, "bust": False, "target": 21}
    assert tool.evaluate(cards + [CardRef("2H", "2", "H", 2)])["total"] == 13


def test_arithmetic_plan_executes_registered_validator_and_rejects_fake_answer():
    raw = {"game_kind": "arithmetic", "players": 1,
           "tools": [{"name": "arithmetic_solver", "config": {"target": 24}}],
           "actions": [{"tool": "arithmetic_solver", "operation": "validate",
                        "args": {"expression": "8/(3-8/3)", "numbers": [3, 3, 8, 8]}, "result_key": "answer"}]}
    result = GameLayer.from_plan(ToolPlan.model_validate(raw)).execute()
    assert result["state"]["answer"] == {"correct": True, "target": 24}
    raw["actions"][0]["args"]["expression"] = "24"
    layer = GameLayer.from_plan(ToolPlan.model_validate(raw))
    with pytest.raises(ToolError):
        layer.execute()
    assert layer.context.events == []


def test_duplicate_tool_declarations_are_rejected():
    with pytest.raises(ValueError, match="tool_plan_duplicate_tool"):
        ToolPlan.model_validate({"game_kind": "test", "players": 1,
                                 "tools": [{"name": "zones"}, {"name": "zones"}]})
