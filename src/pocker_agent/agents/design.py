"""Conversation-only agent. It has no imports from code generation or runtime."""

from __future__ import annotations

import json
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pocker_agent.domain.workspace import DesignDraft, Workspace
from pocker_agent.infrastructure.model_json import parse_object

DESIGN_PROMPT = """你是 Pocker Agent 的纸牌玩法设计伙伴。当前阶段只聊天和整理人类可读规则，绝不生成代码、DSL、ToolPlan或调用引擎。
像正常聊天助手一样回答用户，保留已经确定的规则。重要信息缺失时集中问少量问题；用户可以多轮补充、修改或询问。
明确的人数、牌组与大小顺序、起手/发牌方式、合法动作和轮转、胜负/平局/结束条件都确定后，整理完整规则摘要等待用户点击“确认规则并生成游戏”。
如果用户接受你提出的默认值，可将其写入摘要；未征求意见不能擅自替用户决定关键规则。
玩法支持纸牌规则和本机单人对电脑；不能声称支持多人联网、实时同步、支付或外部服务。用户询问能力时据此说明。
即使用户在聊天中说“生成”“确认”或要求使用代码，也只复述待确认规则；程序只有在用户点击确认按钮后才会构建。
只返回 JSON：{"message":"自然对话回复","ready":false,"draft":null}。
规则完整可供确认时返回 {"message":"简短说明并邀请核对","ready":true,"draft":{"title":"游戏名称","summary":"完整、独立可读的中文规则，含以上所有关键条件"}}。
修改现有规则后必须重新提供完整摘要；存在新的未决条件时 ready=false，draft=null。不能输出源码或假装游戏已创建。
"""


class DesignReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=12000)
    ready: bool
    draft: DesignDraft | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_shape(cls, value):
        if not isinstance(value, dict):
            return value
        if value.get("type") == "question":
            return {
                "message": value.get("question", "请补充玩法细节"),
                "ready": False,
                "draft": None,
            }
        if value.get("type") == "proposal" and isinstance(value.get("rules"), dict):
            rules = value["rules"]
            return {
                "message": value.get("summary", "规则已整理，请核对后确认"),
                "ready": True,
                "draft": {
                    "title": rules.get("title", "未命名游戏"),
                    "summary": rules.get(
                        "description", json.dumps(rules, ensure_ascii=False)
                    ),
                },
            }
        return value

    @model_validator(mode="after")
    def valid_readiness(self):
        if self.ready != (self.draft is not None):
            raise ValueError(
                "ready=true requires a complete draft; unresolved rules require draft=null"
            )
        if not self.message.strip():
            raise ValueError("empty design reply")
        return self


class DesignAgent:
    def __init__(self, model_factory: Callable):
        self.model_factory = model_factory

    def reply(self, workspace: Workspace, context) -> tuple[str, DesignDraft | None]:
        model = self.model_factory()
        model.timeout_seconds = 90
        if hasattr(model, "cancel"):
            context.on_cancel(model.cancel)
        messages = [{"role": "system", "content": DESIGN_PROMPT}]
        if workspace.draft:
            messages.append(
                {
                    "role": "system",
                    "content": "当前规则草稿：" + workspace.draft.model_dump_json(),
                }
            )
        # Conversation storage is lossless. The model sees a bounded recent window
        # plus the current full draft, so old code or huge histories cannot dominate.
        messages.extend(message.model_dump() for message in workspace.messages[-24:])
        context.progress("正在理解规则并回复")
        raw = model.complete(messages, response_format={"type": "json_object"})
        context.check()
        response = DesignReply.model_validate(parse_object(raw))
        return response.message, response.draft
