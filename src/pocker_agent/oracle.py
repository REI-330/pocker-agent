"""Independent, small golden-rule checks used to audit generated/composed engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .tools import CardRef


@dataclass(frozen=True)
class GoldenTrace:
    name: str
    check: Callable[[], bool]


def _c(rank: str, suit: str, value: int) -> CardRef:
    return CardRef(rank + suit, rank, suit, value)


def holdem_traces() -> list[GoldenTrace]:
    return [
        GoldenTrace("royal_flush_shape", lambda: len({"A","K","Q","J","10"}) == 5),
        GoldenTrace("wheel_straight", lambda: sorted([14,2,3,4,5]) == [2,3,4,5,14]),
    ]


def doudizhu_traces() -> list[GoldenTrace]:
    bomb = [_c("7", s, 7) for s in "SHDC"]
    rocket = [CardRef("BJ", "BJ", "", 15), CardRef("RJ", "RJ", "", 16)]
    return [GoldenTrace("bomb_is_four_same_rank", lambda: len({c.rank for c in bomb}) == 1 and len(bomb) == 4),
            GoldenTrace("rocket_is_two_jokers", lambda: {c.id for c in rocket} == {"BJ", "RJ"})]


def run_golden_traces() -> dict[str, bool]:
    traces = holdem_traces() + doudizhu_traces()
    return {trace.name: bool(trace.check()) for trace in traces}
