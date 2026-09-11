from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ToolAction(BaseModel):
    """A declarative, reviewable call; arbitrary Python is never accepted."""
    model_config = ConfigDict(extra="forbid")
    tool: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    operation: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    args: dict[str, Any] = Field(default_factory=dict)
    result_key: str | None = Field(default=None, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")

