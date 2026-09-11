from __future__ import annotations
from dataclasses import dataclass, field
import random
from .core import CardRef, ToolError

@dataclass
class DrawDiscardTool:
    """摸一张/多张、弃牌和弃牌堆顶牌保护的通用账本。"""
    stock: list[CardRef] = field(default_factory=list)
    discard: list[CardRef] = field(default_factory=list)

    def draw(self, hand: list[CardRef], count: int = 1, recycle: bool = False,
             recycle_seed: int | str = 0) -> list[CardRef]:
        if type(count) is not int or count < 0: raise ToolError("invalid_draw_count")
        drawn = []
        for _ in range(count):
            if not self.stock:
                if not recycle or len(self.discard) <= 1: break
                # Keep the list identities: callers may bind them to persisted
                # game state. Shuffle only the covered discards, never the top.
                self.stock.extend(self.discard[:-1])
                self.discard[:] = self.discard[-1:]
                random.Random(recycle_seed).shuffle(self.stock)
            card = self.stock.pop(); hand.append(card); drawn.append(card)
        return drawn

    def discard_cards(self, hand: list[CardRef], cards: list[CardRef]) -> CardRef | None:
        ids = [self._id(c) for c in cards]
        if not ids or len(ids) != len(set(ids)) or any(self._id(c) not in {self._id(x) for x in hand} for c in cards):
            raise ToolError("card_not_in_hand")
        lookup = {self._id(c): c for c in hand}
        if any(lookup[self._id(c)] != c for c in cards): raise ToolError("card_identity_mismatch")
        hand[:] = [c for c in hand if self._id(c) not in set(ids)]; self.discard.extend(cards)
        return self.discard[-1]

    def top(self) -> CardRef | None: return self.discard[-1] if self.discard else None
    @staticmethod
    def _id(card): return getattr(card, "id", (getattr(card, "suit", ""), getattr(card, "rank", ""), getattr(card, "value", 0)))


@dataclass
class DrawUntilPlayableTool:
    recycle: bool = True
    wild_ranks: tuple[str, ...] = ()
    def draw_until_playable(self, hand, stock, discard, *, top=None, active_suit=None, recycle_seed=0):
        import random
        drawn=[]; top = top if top is not None else (discard[-1] if discard else None)
        while True:
            if any(self._matches(card, top, active_suit) for card in hand): return {"drawn": drawn, "playable": True, "hand_size": len(hand)}
            if not stock:
                if not self.recycle or len(discard) <= 1: return {"drawn": drawn, "playable": False, "hand_size": len(hand)}
                stock.extend(discard[:-1]); del discard[:-1]; random.Random(recycle_seed).shuffle(stock)
            card=stock.pop(); hand.append(card); drawn.append(card)
    def _matches(self, card, top, active_suit):
        if top is None: return True
        return card.rank in self.wild_ranks or card.suit == active_suit or card.suit == top.suit or card.rank == top.rank
