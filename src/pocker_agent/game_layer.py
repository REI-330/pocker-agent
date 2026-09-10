from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tools import ToolContext, ToolRegistry, default_registry
from .tools.plan import ToolPlan


@dataclass
class GameLayer:
    """Small orchestration boundary between an Agent Tool Plan and a runtime.

    It intentionally does not implement game rules: configured tools own those
    invariants and this layer only records composition and shared context.
    """

    plan: dict[str, Any]
    registry: ToolRegistry = field(default_factory=default_registry)
    context: ToolContext = field(default_factory=ToolContext)
    tools: dict[str, Any] = field(default_factory=dict)

    def configure(self) -> "GameLayer":
        for item in self.plan.get("tools", []):
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValueError("invalid_tool_plan")
            name = item["name"]
            config = item.get("config", {}) if "config" in item else {k: v for k, v in item.items() if k != "name"}
            self.tools[name] = self.registry.create(name, **config)
        return self

    @classmethod
    def from_plan(cls, plan: ToolPlan, registry: ToolRegistry | None = None) -> "GameLayer":
        layer = cls(plan.model_dump(mode="python"), registry or default_registry())
        return layer.configure()

    def describe(self) -> dict[str, Any]:
        return {"game_kind": self.plan.get("game_kind"), "tools": sorted(self.tools),
                "players": self.plan.get("players"), "configured": bool(self.tools)}

    def execute(self) -> dict[str, Any]:
        from .rule_executor import RuleExecutor
        return RuleExecutor(self).run()
