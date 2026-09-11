from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence
from .core import ToolError

@dataclass
class WinConditionTool:
    conditions: list[dict[str, Any]] | None = None
    def check(self, state: dict[str, Any], condition: str | None = None) -> dict[str, Any]:
        name = condition or ((self.conditions or [{}])[0].get("type"))
        if not isinstance(name, str): raise ToolError("win_condition_missing")
        if name == "hand_empty": winners = [p for p,n in state.get("hand_sizes", {}).items() if n == 0]
        elif name == "target_score": winners = [p for p,n in state.get("scores", {}).items() if isinstance(state.get("target"), int) and n >= state["target"]]
        elif name == "last_player": winners = list(state.get("active_players", [])); winners = winners if len(winners) == 1 else []
        elif name == "no_legal_action": winners = list(state.get("winner_candidates", [])) if not state.get("legal_actions") else []
        else: raise ToolError(f"unknown_win_condition:{name}")
        return {"condition": name, "finished": bool(winners), "winners": winners}

@dataclass
class SettlementTool:
    player_count: int
    scores: list[int] | None = None
    def __post_init__(self):
        if type(self.player_count) is not int or self.player_count < 1: raise ToolError("invalid_player_count")
        self.scores = [0]*self.player_count if self.scores is None else list(self.scores)
        if len(self.scores) != self.player_count or any(type(x) is not int for x in self.scores): raise ToolError("invalid_scores")
    def settle(self, deltas: Sequence[int]) -> dict[str, Any]:
        if len(deltas) != self.player_count or any(type(x) is not int for x in deltas): raise ToolError("invalid_settlement")
        if sum(deltas) != 0: raise ToolError("settlement_not_conserved")
        self.scores = [a+b for a,b in zip(self.scores, deltas)]
        return {"scores": list(self.scores), "deltas": list(deltas), "settled": True}
