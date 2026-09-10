from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .core import CardRef, ToolError

_WILD = {"BJ", "RJ"}


@dataclass(frozen=True)
class DoudizhuHand:
    kind: str
    rank: int
    length: int = 1
    wing: str = ""

    def key(self) -> tuple:
        return (self.kind, self.rank, self.length)


def classify(cards: Iterable[CardRef]) -> DoudizhuHand:
    cards = list(cards)
    if not cards or len(cards) > 20:
        raise ToolError("invalid_doudizhu_hand_size")
    rank_map = {"J": 11, "Q": 12, "K": 13, "A": 14, "2": 15}
    ranks = [16 if c.id == "BJ" else 17 if c.id == "RJ" else rank_map.get(c.rank, c.value) for c in cards]
    counts = Counter(ranks)
    unique = sorted(counts)
    if set(ranks) == {16, 17} and len(ranks) == 2:
        return DoudizhuHand("rocket", 17)
    if len(cards) == 4 and len(counts) == 1:
        return DoudizhuHand("bomb", unique[0])
    if len(cards) == 1: return DoudizhuHand("single", unique[0])
    if len(cards) == 2 and len(counts) == 1: return DoudizhuHand("pair", unique[0])
    if len(cards) == 3 and len(counts) == 1: return DoudizhuHand("triple", unique[0])
    if len(cards) == 4 and 3 in counts.values(): return DoudizhuHand("triple_single", max(r for r,n in counts.items() if n == 3))
    if len(cards) == 5 and sorted(counts.values()) == [2, 3]:
        triple = next(r for r, n in counts.items() if n == 3)
        return DoudizhuHand("triple_pair", triple)
    if len(cards) >= 5 and len(counts) == len(cards) and _consecutive(unique):
        return DoudizhuHand("straight", unique[-1], len(cards))
    if len(cards) >= 6 and len(cards) % 2 == 0 and all(n == 2 for n in counts.values()) and _consecutive(unique):
        return DoudizhuHand("consecutive_pairs", unique[-1], len(unique))
    if len(cards) >= 6 and len(cards) % 3 == 0 and all(n == 3 for n in counts.values()) and _consecutive(unique):
        return DoudizhuHand("airplane", unique[-1], len(unique))
    triples = sorted(r for r, n in counts.items() if n >= 3)
    if len(triples) >= 2 and _consecutive(triples):
        need = 3 * len(triples)
        if len(cards) == need + len(triples):
            remainder = list(ranks)
            for rank in triples:
                remainder.remove(rank); remainder.remove(rank); remainder.remove(rank)
            if len(remainder) == len(triples): return DoudizhuHand("airplane_single_wing", triples[-1], len(triples))
        if len(cards) == need + 2 * len(triples):
            remainder = list(ranks)
            for rank in triples:
                remainder.remove(rank); remainder.remove(rank); remainder.remove(rank)
            if all(remainder.count(r) == 2 for r in set(remainder)) and len(set(remainder)) == len(triples):
                return DoudizhuHand("airplane_pair_wing", triples[-1], len(triples))
    if len(cards) in {6, 8} and 4 in counts.values() and sum(n for n in counts.values() if n != 4) == len(cards) - 4:
        return DoudizhuHand("four_with_two", max((r for r, n in counts.items() if n == 4), default=0), len(cards))
    raise ToolError("unsupported_or_invalid_doudizhu_combination")


def _consecutive(values: list[int]) -> bool:
    return bool(values) and values[-1] <= 14 and values == list(range(values[0], values[-1] + 1))


def beats(current: DoudizhuHand, previous: DoudizhuHand) -> bool:
    if current.kind == "rocket": return True
    if previous.kind == "rocket": return False
    if current.kind == "bomb" and previous.kind != "bomb": return True
    if current.kind != previous.kind or current.length != previous.length: return False
    return current.rank > previous.rank
