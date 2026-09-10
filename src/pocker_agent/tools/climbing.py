from __future__ import annotations
from .core import ToolError

def climb_beats(current: dict, previous: dict | None, *, type_order: list[str] | None = None) -> bool:
    """Compare normalized combination descriptors: kind, rank, length."""
    if not isinstance(current, dict) or previous is not None and not isinstance(previous, dict):
        raise ToolError("invalid_combination_descriptor")
    if previous is None: return True
    order = type_order or ["single", "pair", "triple", "straight", "bomb", "rocket"]
    if current.get("kind") == "rocket": return True
    if previous.get("kind") == "rocket": return False
    if current.get("kind") == "bomb" and previous.get("kind") != "bomb": return True
    if current.get("kind") != previous.get("kind") or current.get("length", 1) != previous.get("length", 1): return False
    if current.get("kind") not in order: raise ToolError("unknown_combination_kind")
    return int(current.get("rank", -1)) > int(previous.get("rank", -1))
