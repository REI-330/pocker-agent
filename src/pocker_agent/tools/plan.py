from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    config: dict[str, Any] = Field(default_factory=dict)

class ToolAction(BaseModel):
    """A declarative, reviewable call; arbitrary Python is never accepted."""
    model_config = ConfigDict(extra="forbid")
    tool: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    operation: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    args: dict[str, Any] = Field(default_factory=dict)
    result_key: str | None = Field(default=None, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")


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
    end_conditions: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def distinct_tools(self):
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("tool_plan_duplicate_tool")
        if any(action.tool not in names for action in self.actions):
            raise ValueError("tool_action_not_declared")
        return self
