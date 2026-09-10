from __future__ import annotations

from pathlib import Path


class CardAssetRegistry:
    """Map canonical IDs to existing SVG assets, with a safe text fallback."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).parent / "assets" / "cards"

    def asset(self, card_id: str) -> str | None:
        rank, suit = self._split(card_id)
        names = {"A": "ace", "J": "jack", "Q": "queen", "K": "king"}
        rank_name = names.get(rank, rank)
        suit_name = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}.get(suit)
        if card_id == "BJ": filename = "black_joker.svg"
        elif card_id == "RJ": filename = "red_joker.svg"
        elif suit_name: filename = f"{rank_name}_of_{suit_name}.svg"
        else: return None
        path = self.root / filename
        return f"/assets/cards/{filename}" if path.exists() else None

    @staticmethod
    def _split(card_id: str) -> tuple[str, str]:
        if card_id in {"BJ", "RJ"}: return card_id, ""
        return card_id[:-1], card_id[-1:]
