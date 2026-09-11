from __future__ import annotations
from dataclasses import dataclass


def doudizhu_multiplier(base_bid: int, bombs: int = 0, rocket: bool = False, spring: bool = False) -> int:
    """Official-style practice scoring: each bomb/rocket/spring doubles."""
    multiplier = 2 ** (max(0, bombs) + (1 if rocket else 0) + (1 if spring else 0))
    return base_bid * multiplier


def doudizhu_scores(base_bid: int, landlord: int, winner: int, player_count: int = 3, **kwargs) -> list[int]:
    amount = doudizhu_multiplier(base_bid, **kwargs)
    if winner == landlord:
        return [amount * 2 if i == landlord else -amount for i in range(player_count)]
    return [-amount * 2 if i == landlord else amount for i in range(player_count)]

@dataclass
class DoudizhuSettlementTool:
    player_count: int = 3

    def settle(self, base_bid: int, landlord: int, winner: int, **kwargs) -> list[int]:
        return doudizhu_scores(base_bid, landlord, winner, self.player_count, **kwargs)


def resolve_winners(values, mode: str = "max") -> list[int]:
    """Resolve tied winners from comparable values. Returns all tied indexes."""
    values = list(values)
    if not values:
        return []
    if mode == "min":
        target = min(values)
    elif mode == "max":
        target = max(values)
    else:
        raise ValueError("invalid_winner_mode")
    return [index for index, value in enumerate(values) if value == target]


def settle_scores(scores, winners, points: int = 1) -> list[int]:
    """Apply a deterministic round award and return the resulting score list."""
    result = list(scores)
    for index in winners:
        if not isinstance(index, int) or not 0 <= index < len(result):
            raise ValueError("invalid_winner_index")
        result[index] += points
    return result
