from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from .core import ToolError

@dataclass
class TriggerTool:
    handlers: dict[str, list[Callable[[dict[str, Any]], Any]]] = field(default_factory=dict)
    def on(self, event: str, handler: Callable[[dict[str, Any]], Any]):
        if not event or not callable(handler): raise ToolError("invalid_trigger")
        self.handlers.setdefault(event, []).append(handler)
    def emit(self, event: str, payload: dict[str, Any] | None = None) -> list[Any]:
        return [handler(dict(payload or {})) for handler in self.handlers.get(event, [])]
