from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from functools import partial
from inspect import signature

from .core import ToolError


@dataclass
class ToolRegistry:
    _factories: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        if not name or name in self._factories:
            raise ToolError("tool_name_missing_or_duplicate")
        self._factories[name] = factory

    def create(self, name: str, **config: Any) -> Any:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise ToolError(f"unknown_tool:{name}") from exc
        try:
            return factory(**config)
        except TypeError as exc:
            raise ToolError(f"invalid_tool_config:{name}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_registry() -> ToolRegistry:
    from .core import DeckTool
    from .arithmetic_solver import ArithmeticSolverTool
    from .betting import PotTool
    from .ranking import HandRankTool, best_of
    from .doudizhu import classify
    from .zones import ZoneTool
    from .turns import TurnOrderTool
    from .matching import matches, follow_suit, group_by
    from .conditions import evaluate
    from .patterns import resolve_trick, detect_meld
    from .draw_discard import DrawDiscardTool
    from .climbing import climb_beats
    from .triggers import TriggerTool
    from .holdem import BettingRoundTool, PhaseProgressTool, CommunityDealTool, AllInTool, showdown, settle_pots
    from .gameflow import WinConditionTool, SettlementTool
    from .settlement import resolve_winners, settle_scores, DoudizhuSettlementTool
    from .state_ops import StateTool, LogicTool, PointContestTool, DealerPolicyTool, ArithmeticDealTool, SheddingTurnTool, DoudizhuTurnTool
    def function_tool(function):
        def configure(**config):
            signature(function).bind_partial(**config)
            return partial(function, **config)
        return configure
    registry = ToolRegistry()
    registry.register("deck", DeckTool)
    registry.register("pot", PotTool)
    registry.register("holdem_hand_rank", lambda **_: best_of)
    registry.register("doudizhu_hand_rank", lambda **_: classify)
    registry.register("hand_rank", HandRankTool)
    registry.register("zones", ZoneTool)
    registry.register("turn_order", TurnOrderTool)
    registry.register("card_match", function_tool(matches))
    registry.register("follow_suit", function_tool(follow_suit))
    registry.register("group_cards", function_tool(group_by))
    registry.register("condition", function_tool(evaluate))
    registry.register("trick_resolve", function_tool(resolve_trick))
    registry.register("meld_detect", function_tool(detect_meld))
    registry.register("draw_discard", DrawDiscardTool)
    registry.register("climb_beats", function_tool(climb_beats))
    registry.register("triggers", TriggerTool)
    registry.register("betting_round", BettingRoundTool)
    registry.register("phase_progress", PhaseProgressTool)
    registry.register("community_deal", CommunityDealTool)
    registry.register("all_in", AllInTool)
    registry.register("showdown", function_tool(showdown))
    registry.register("settle_pots", function_tool(settle_pots))
    registry.register("side_pots", function_tool(settle_pots))
    registry.register("win_condition", WinConditionTool)
    registry.register("settlement", SettlementTool)
    registry.register("winner_resolve", function_tool(resolve_winners))
    registry.register("score_settle", function_tool(settle_scores))
    registry.register("doudizhu_settle", DoudizhuSettlementTool)
    registry.register("arithmetic_solver", ArithmeticSolverTool)
    registry.register("state", StateTool)
    registry.register("logic", LogicTool)
    registry.register("point_contest", PointContestTool)
    registry.register("dealer_policy", DealerPolicyTool)
    registry.register("arithmetic_deal", ArithmeticDealTool)
    registry.register("shedding_turn", SheddingTurnTool)
    registry.register("doudizhu_turn", DoudizhuTurnTool)
    return registry
