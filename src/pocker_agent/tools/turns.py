from __future__ import annotations
from dataclasses import dataclass
from .core import ToolError

@dataclass
class TurnOrderTool:
    players: list[str]
    current: int = 0
    direction: int = 1
    passes: int = 0
    def __post_init__(self):
        self.players = list(self.players)
        if not self.players or len(set(self.players)) != len(self.players) or any(not isinstance(p, str) or not p for p in self.players): raise ToolError("unique_players_required")
        if type(self.current) is not int or not 0 <= self.current < len(self.players): raise ToolError("invalid_current_player")
        if type(self.direction) is not int or self.direction not in {-1, 1}: raise ToolError("invalid_direction")
        if type(self.passes) is not int or self.passes < 0: raise ToolError("invalid_pass_count")
    def current_player(self): return self.players[self.current]
    def advance(self, steps: int = 1):
        if type(steps) is not int or steps < 0: raise ToolError("invalid_turn_steps")
        self.current = (self.current + self.direction * steps) % len(self.players); return self.current_player()
    def reverse(self): self.direction *= -1; return self.direction
    def pass_turn(self): self.passes += 1; return self.advance()
    def reset_passes(self): self.passes = 0
