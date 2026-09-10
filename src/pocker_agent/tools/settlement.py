from __future__ import annotations


def doudizhu_multiplier(base_bid: int, bombs: int = 0, rocket: bool = False, spring: bool = False) -> int:
    """Official-style practice scoring: each bomb/rocket/spring doubles."""
    multiplier = 2 ** (max(0, bombs) + (1 if rocket else 0) + (1 if spring else 0))
    return base_bid * multiplier


def doudizhu_scores(base_bid: int, landlord: int, winner: int, player_count: int = 3, **kwargs) -> list[int]:
    amount = doudizhu_multiplier(base_bid, **kwargs)
    if winner == landlord:
        return [amount * 2 if i == landlord else -amount for i in range(player_count)]
    return [-amount * 2 if i == landlord else amount for i in range(player_count)]
