from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable


class ToolError(ValueError):
    """A deterministic tool rejected an operation."""


@dataclass(frozen=True)
class CardRef:
    id: str
    rank: str
    suit: str
    value: int

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "rank": self.rank, "suit": self.suit, "value": self.value}


@dataclass
class ToolContext:
    seed: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: str, **payload: Any) -> dict[str, Any]:
        item = {"event": event, **payload}
        self.events.append(item)
        return item


@dataclass(frozen=True)
class ToolResult:
    value: Any
    events: tuple[dict[str, Any], ...] = ()


class DeckTool:
    """Create and deal canonical card IDs; no UI or game-specific rules."""

    name = "deck"

    def __init__(self, ranks: list[str], suits: list[str], copies: int = 1, excluded: set[str] | None = None):
        self.ranks, self.suits, self.copies = list(ranks), list(suits), copies
        self.excluded = excluded or set()

    def cards(self) -> list[CardRef]:
        standard = {"A": 14, "J": 11, "Q": 12, "K": 13}
        def value(rank: str, index: int) -> int:
            if rank in standard: return standard[rank]
            try: return int(rank)
            except ValueError: return index + 1
        return [CardRef(f"{rank}{suit}", rank, suit, value(rank, index + 1))
                for _ in range(self.copies) for index, rank in enumerate(self.ranks)
                for suit in self.suits if f"{rank}{suit}" not in self.excluded]

    def shuffled(self, seed: int | str) -> list[CardRef]:
        cards = self.cards()
        random.Random(seed).shuffle(cards)
        return cards

    def deal(self, seed: int, hands: int, cards_each: int, kitty: int = 0) -> ToolResult:
        if hands < 1 or cards_each < 0 or kitty < 0:
            raise ToolError("invalid_deal_parameters")
        deck = self.shuffled(seed)
        needed = hands * cards_each + kitty
        if needed > len(deck):
            raise ToolError("deck_exhausted")
        dealt = [deck[i * cards_each:(i + 1) * cards_each] for i in range(hands)]
        rest = deck[hands * cards_each:]
        return ToolResult({"hands": dealt, "kitty": rest[:kitty], "deck": rest[kitty:]})

    def deal_into(self, stock: list, hands: list[list], cards_each: int = 1) -> int:
        """Deal round-robin into canonical hands, checking capacity before mutation."""
        if type(cards_each) is not int or cards_each < 0 or not hands:
            raise ToolError("invalid_deal_parameters")
        if any(hand is stock for hand in hands) or len({id(hand) for hand in hands}) != len(hands):
            raise ToolError("invalid_deal_destinations")
        needed = len(hands) * cards_each
        if needed > len(stock):
            raise ToolError("deck_exhausted")
        for _ in range(cards_each):
            for hand in hands:
                hand.append(stock.pop())
        return needed

    def draw(self, stock: list, hand: list, count: int = 1) -> int:
        return self.deal_into(stock, [hand], count)
