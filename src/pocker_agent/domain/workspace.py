"""State shared by design, generation and play use cases; no IO or model calls."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Phase(StrEnum):
    DESIGNING = "designing"
    THINKING = "thinking"
    PROPOSAL_READY = "proposal_ready"
    BUILDING = "building"
    PLAYABLE = "playable"
    FAILED = "failed"


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DesignDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=16000)


class Progress(BaseModel):
    message: str
    time: float


class Job(BaseModel):
    id: str
    kind: Literal["chat", "build"]
    status: Literal["running", "completed", "failed", "cancelled"] = "running"
    progress: list[Progress] = Field(default_factory=list)
    error: str | None = None


class Workspace(BaseModel):
    id: str
    revision: int = 0
    phase: Phase = Phase.DESIGNING
    messages: list[Message] = Field(default_factory=list)
    draft: DesignDraft | None = None
    # Only a successful build may publish executable artifacts.
    proposal: dict[str, Any] | None = None
    facts: list[str] = Field(default_factory=list)
    tool_plan: dict[str, Any] | None = None
    contract: dict[str, Any] | None = None
    verification: list[dict[str, Any]] = Field(default_factory=list)
    job: Job | None = None
    error: str | None = None
    runtime_id: str | None = None
    request_ids: dict[str, str] = Field(default_factory=dict, exclude=True)

    def invalidate_game(self) -> None:
        self.proposal = None
        self.facts = []
        self.tool_plan = None
        self.contract = None
        self.verification = []
        self.runtime_id = None

    @property
    def active(self) -> bool:
        return self.phase in {Phase.THINKING, Phase.BUILDING}

    def owns(self, operation_id: str) -> bool:
        return bool(
            self.active
            and self.job
            and self.job.id == operation_id
            and self.job.status == "running"
        )
