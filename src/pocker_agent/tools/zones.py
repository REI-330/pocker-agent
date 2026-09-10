from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .core import CardRef, ToolError

@dataclass
class ZoneTool:
    """牌区与可见性账本；不包含具体玩法规则。"""
    zones: dict[str, list[CardRef]] = field(default_factory=dict)
    visibility: dict[str, set[str]] = field(default_factory=dict)

    def create(self, name: str, cards: list[CardRef] | None = None, visible_to: set[str] | None = None):
        if not name or name in self.zones: raise ToolError("zone_name_missing_or_duplicate")
        cards = list(cards or [])
        ids = [c.id for c in cards]
        existing = {c.id for zone in self.zones.values() for c in zone}
        if len(ids) != len(set(ids)) or existing.intersection(ids):
            raise ToolError("duplicate_card_id")
        self.zones[name] = list(cards or []); self.visibility[name] = set(visible_to or set()); return name
    def move(self, source: str, target: str, cards: list[CardRef] | None = None, count: int | None = None):
        if source not in self.zones or target not in self.zones: raise ToolError("unknown_zone")
        if source == target: raise ToolError("same_source_and_target")
        if cards is not None and count is not None: raise ToolError("ambiguous_card_selection")
        if cards is None:
            count = 1 if count is None else count
            if type(count) is not int or not 0 <= count <= len(self.zones[source]):
                raise ToolError("invalid_draw_count")
        selected = list(cards) if cards is not None else (self.zones[source][-count:] if count else [])
        ids = [c.id for c in selected]
        if len(set(ids)) != len(ids) or any(c.id not in {x.id for x in self.zones[source]} for c in selected): raise ToolError("card_not_in_source_zone")
        originals = {c.id: c for c in self.zones[source]}
        if any(originals[c.id] != c for c in selected): raise ToolError("card_identity_mismatch")
        self.zones[source] = [c for c in self.zones[source] if c.id not in set(ids)]; self.zones[target].extend(selected); return selected
    def reveal(self, zone: str, players: set[str]):
        if zone not in self.zones: raise ToolError("unknown_zone")
        self.visibility[zone] = set(players); return sorted(players)
    def hide(self, zone: str): return self.reveal(zone, set())
    def view(self, zone: str, player: str | None = None) -> list[dict[str, Any]]:
        if zone not in self.zones: raise ToolError("unknown_zone")
        return [c.as_dict() if player in self.visibility[zone] or "*" in self.visibility[zone] else {"hidden": True} for c in self.zones[zone]]
