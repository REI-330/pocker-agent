"""Serializable control flow for ToolPlans; no game-family dispatch."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .actions import ToolAction


class FlowCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Any
    target: str


class FlowNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["call", "branch", "wait", "end"]
    action: ToolAction | None = None
    next: str | None = None
    value: Any = None
    cases: list[FlowCase] = Field(default_factory=list, max_length=32)
    inputs: dict[str, str] = Field(default_factory=dict)
    available_actions: Any = None
    default_action: Any = None

    @model_validator(mode="after")
    def complete_node(self):
        if self.kind == "call" and (self.action is None or self.next is None):
            raise ValueError("flow_call_requires_action_and_next")
        if self.kind == "branch" and (not self.cases or self.next is None):
            raise ValueError("flow_branch_requires_cases_and_default")
        if self.kind == "wait" and not self.inputs:
            raise ValueError("flow_wait_requires_inputs")
        if self.kind != "call" and self.action is not None:
            raise ValueError("flow_action_only_on_call")
        return self


class FlowProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry: str
    initial: dict[str, Any] = Field(default_factory=dict)
    nodes: dict[str, FlowNode] = Field(min_length=1, max_length=256)
    step_limit: int = Field(default=512, ge=1, le=4096)

    @model_validator(mode="after")
    def valid_edges(self):
        if self.entry not in self.nodes:
            raise ValueError("flow_entry_missing")
        for node in self.nodes.values():
            targets = list(node.inputs.values()) + [case.target for case in node.cases]
            if node.next is not None:
                targets.append(node.next)
            if any(target not in self.nodes for target in targets):
                raise ValueError("flow_target_missing")
        return self
