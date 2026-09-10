from __future__ import annotations
from .core import CardRef, ToolError

def matches(card: CardRef, top: CardRef | None, *, fields=("suit", "rank"), wild_ranks=(), active_suit=None):
    if not fields or not set(fields) <= {"rank", "suit", "value"}: raise ToolError("invalid_card_field")
    if top is None: return True
    return card.rank in set(wild_ranks) or any(
        getattr(card, f) == (active_suit if f == "suit" and active_suit is not None else getattr(top, f))
        for f in fields)

def follow_suit(cards: list[CardRef], led: CardRef | None, *, card: CardRef, must_follow=True):
    if card not in cards: return False
    if not led or not must_follow: return True
    return card.suit == led.suit or not any(c.suit == led.suit for c in cards)

def group_by(cards: list[CardRef], field: str = "rank"):
    if field not in {"rank", "suit", "value"}: raise ToolError("invalid_card_field")
    result = {}
    for card in cards: result.setdefault(getattr(card, field), []).append(card)
    return result
