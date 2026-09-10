"""Configurable comparison primitives, independent of game names."""
from .core import CardRef, ToolError

STANDARD_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def rank_positions(cards: list[CardRef], rank_order: list[str] | None):
    order = STANDARD_RANKS if rank_order is None else rank_order
    if not order or len(set(order)) != len(order):
        raise ToolError("unique_rank_order_required")
    if not cards or len(cards) > 104 or len({c.id for c in cards}) != len(cards):
        raise ToolError("invalid_card_selection")
    positions = {rank: i for i, rank in enumerate(order)}
    if any(c.rank not in positions for c in cards):
        raise ToolError("rank_missing_from_order")
    return positions


def resolve_trick(cards: list[CardRef], *, trump: str | None = None,
                  rank_order: list[str] | None = None) -> dict:
    """Resolve a completed trick in play order; the first card defines lead suit.

    Legality (following suit, completed participant list) is checked by the
    caller before resolution. Suitless ranking alone cannot validate a trick.
    """
    positions = rank_positions(cards, rank_order)
    led = cards[0].suit
    eligible = [i for i, c in enumerate(cards) if trump is not None and c.suit == trump]
    if not eligible:
        eligible = [i for i, c in enumerate(cards) if c.suit == led]
    winner = max(eligible, key=lambda i: positions[cards[i].rank])
    return {"winner_index": winner, "card_id": cards[winner].id, "led_suit": led}


def detect_meld(cards: list[CardRef], *, rank_order: list[str] | None = None,
                min_size: int = 3, max_group_size: int = 4) -> dict:
    """Classify a selected natural set/run, without wildcards or wraparound.

    A-low games provide A,2,...,K as rank_order. Enumerating an optimal hand
    partition/deadwood is a separate operation and is not claimed here.
    """
    positions = rank_positions(cards, rank_order)
    if type(min_size) is not int or min_size < 2 or type(max_group_size) is not int or max_group_size < min_size:
        raise ToolError("invalid_meld_limits")
    kind = None
    if len(cards) >= min_size:
        if (len({c.rank for c in cards}) == 1 and len(cards) <= max_group_size
                and len({c.suit for c in cards}) == len(cards)):
            kind = "set"
        values = sorted(positions[c.rank] for c in cards)
        if (len({c.suit for c in cards}) == 1
                and values == list(range(values[0], values[0] + len(cards)))):
            kind = "run"
    return {"valid": kind is not None, "kind": kind, "size": len(cards)}
