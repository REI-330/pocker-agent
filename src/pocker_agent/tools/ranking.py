from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable
from dataclasses import dataclass

from .core import CardRef, ToolError


def _cards(cards: Iterable[CardRef], minimum: int, maximum: int) -> list[CardRef]:
    result = list(cards)
    if not minimum <= len(result) <= maximum:
        raise ToolError(f"expected_{minimum}_to_{maximum}_cards")
    if len({c.id for c in result}) != len(result):
        raise ToolError("duplicate_card")
    if any(c.suit not in {"S", "H", "D", "C"} or c.rank not in
           {"A", "K", "Q", "J", *map(str, range(2, 11))} for c in result):
        raise ToolError("standard_poker_cards_required")
    return result


def _five(cards: list[CardRef]) -> tuple[int, tuple[int, ...]]:
    # Strength belongs to the rule, independently of a deck's display ordering.
    face = {"A": 14, "K": 13, "Q": 12, "J": 11}
    values = sorted((face[c.rank] if c.rank in face else int(c.rank) for c in cards), reverse=True)
    counts = Counter(values)
    flush = len({c.suit for c in cards}) == 1
    unique = sorted(counts, reverse=True)
    high = (5 if unique == [14, 5, 4, 3, 2] else unique[0]
            if len(unique) == 5 and unique[0] - unique[-1] == 4 else 0)
    groups = sorted(((n, v) for v, n in counts.items()), reverse=True)
    if high and flush:
        return 8, (high,)
    if groups[0][0] == 4:
        return 7, (groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return 6, (groups[0][1], groups[1][1])
    if flush:
        return 5, tuple(values)
    if high:
        return 4, (high,)
    if groups[0][0] == 3:
        return 3, (groups[0][1], *sorted((v for n, v in groups[1:]), reverse=True))
    if groups[0][0] == groups[1][0] == 2:
        return 2, (*sorted((groups[0][1], groups[1][1]), reverse=True), groups[2][1])
    if groups[0][0] == 2:
        return 1, (groups[0][1], *sorted((v for n, v in groups[1:]), reverse=True))
    return 0, tuple(values)


def five_card_rank(cards: Iterable[CardRef]) -> tuple[int, tuple[int, ...]]:
    return _five(_cards(cards, 5, 5))


def best_of(cards: Iterable[CardRef]) -> tuple[int, tuple[int, ...]]:
    return max(_five(list(c)) for c in combinations(_cards(cards, 5, 7), 5))


@dataclass
class HandRankTool:
    """Registered hand evaluator shared by blackjack and poker plans.

    ``target`` selects blackjack scoring; without it the callable preserves
    the existing poker ``best_of`` behavior used by generic ToolPlans.
    """

    target: int | None = None
    best_of: int | None = None

    def __post_init__(self):
        if self.target is not None and (type(self.target) is not int or self.target <= 0):
            raise ToolError("invalid_hand_target")
        if self.best_of is not None and self.best_of not in {5, 6, 7}:
            raise ToolError("invalid_best_of_count")

    def evaluate(self, cards: Iterable[CardRef]) -> dict:
        cards = list(cards)
        if self.target is None:
            rank = best_of(cards)
            return {"rank": rank[0], "tiebreak": rank[1]}
        if any(card.rank not in {"A", "J", "Q", "K", *map(str, range(2, 11))} for card in cards):
            raise ToolError("invalid_hand_rank")
        values = [1 if card.rank == "A" else 10 if card.rank in {"J", "Q", "K"}
                  else int(card.rank) for card in cards]
        total = sum(values)
        aces = sum(card.rank == "A" for card in cards)
        soft = aces > 0 and total + 10 <= self.target
        if soft:
            total += 10
        return {"total": total, "soft": soft, "bust": total > self.target,
                "target": self.target}

    def __call__(self, cards: Iterable[CardRef]):
        return best_of(cards) if self.target is None else self.evaluate(cards)

