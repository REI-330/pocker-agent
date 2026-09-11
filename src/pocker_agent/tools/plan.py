from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    config: dict[str, Any] = Field(default_factory=dict)

from .actions import ToolAction
from .flow import FlowProgram


class ToolPlan(BaseModel):
    """Agent-facing, reviewable composition contract; execution remains host-owned."""
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0"
    game_kind: str = Field(min_length=1, max_length=64)
    players: int = Field(ge=1, le=12)
    tools: list[ToolInvocation] = Field(min_length=1, max_length=32)
    phases: list[str] = Field(default_factory=list, max_length=32)
    requirements: list[str] = Field(default_factory=list, max_length=64)
    actions: list[ToolAction] = Field(default_factory=list, max_length=128)
    flow: FlowProgram | None = None
    end_conditions: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def distinct_tools(self):
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("tool_plan_duplicate_tool")
        if any(action.tool not in names for action in self.actions):
            raise ValueError("tool_action_not_declared")
        if self.flow and any(node.action.tool not in names for node in self.flow.nodes.values() if node.action):
            raise ValueError("flow_tool_not_declared")
        return self
