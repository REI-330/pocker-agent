from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .llm import ModelClient
from .models import GameRuleDSL
from .validation import validate_dsl

DSL_SCHEMA_HINT = {
    "schema_version": "0.1",
    "game_id": "lowercase-id",
    "title": "string",
    "description": "string",
    "deck": {"suits": ["S", "H"], "ranks": ["A", "K"], "copies": 1},
    "players": {"min_players": 2, "max_players": 4, "starting_hand_size": 1},
    "phases": [{"name": "main", "actions": ["play"], "max_turns": 100}],
    "actions": [{"name": "play", "source": "hand", "amount": 1}],
    "scoring": [],
    "max_rounds": 1,
}


@dataclass
class AgentTurn:
    kind: str
    message: str
    rules: GameRuleDSL | None = None
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class AgentSession:
    messages: list[dict[str, str]] = field(default_factory=list)
    proposal: dict[str, Any] | None = None
    confirmed: bool = False


class RuleAgent:
    def __init__(self, model: ModelClient):
        self.model = model

    def turn(self, session: AgentSession, user_text: str) -> AgentTurn:
        session.messages.append({"role": "user", "content": user_text})
        prompt = self._system_prompt()
        raw = self.model.complete([{"role": "system", "content": prompt}, *session.messages], response_format={"type": "json_object"})
        result = self._parse_json(raw)
        if result.get("type") == "question":
            question = str(result.get("question", "请补充玩法细节。"))
            session.messages.append({"role": "assistant", "content": question})
            return AgentTurn(kind="question", message=question, missing=[str(item) for item in result.get("missing", [])])
        proposal = result.get("rules", result)
        if not isinstance(proposal, dict):
            return AgentTurn(kind="error", message="模型没有返回可解析的规则对象。", errors=["model_output_not_object"])
        rules, errors = validate_dsl(proposal)
        session.proposal = proposal
        if errors:
            repair, repair_error = self._repair(proposal, errors)
            if repair is not None:
                rules, errors = validate_dsl(repair)
                session.proposal = repair
            elif repair_error:
                errors.append(repair_error)
        if errors:
            return AgentTurn(kind="error", message="规则暂时无法执行，请修正以下问题。", errors=errors)
        summary = str(result.get("summary", "规则已生成，请确认后开始模拟。"))
        return AgentTurn(kind="proposal", message=summary, rules=rules)

    def confirm(self, session: AgentSession) -> AgentTurn:
        if not session.proposal:
            return AgentTurn(kind="error", message="还没有可以确认的规则。", errors=["proposal_missing"])
        rules, errors = validate_dsl(session.proposal)
        if errors:
            return AgentTurn(kind="error", message="规则仍未通过校验。", errors=errors)
        session.confirmed = True
        return AgentTurn(kind="confirmed", message="规则已确认，可以开始模拟。", rules=rules)

    def _repair(self, proposal: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any] | None, str | None]:
        repair_prompt = [
            {"role": "system", "content": "修复 Game Rule DSL，只返回 JSON 对象，不要解释。"},
            {"role": "user", "content": json.dumps({"rules": proposal, "errors": errors}, ensure_ascii=False)},
        ]
        try:
            raw = self.model.complete(repair_prompt, response_format={"type": "json_object"})
            repaired = self._parse_json(raw)
            if not isinstance(repaired, dict):
                return None, "repair_output_not_object"
            return repaired.get("rules", repaired), None
        except RuntimeError as error:
            return None, f"repair_failed:{error}"

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("model_output_invalid_json") from error
        if not isinstance(value, dict):
            raise RuntimeError("model_output_not_object")
        return value

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是 Pocker Agent 的扑克牌规则设计助手。根据对话澄清规则。"
            "Your response must be a valid json object."
            "当关键规则缺失时返回 {type:'question',question:string,missing:string[]}。"
            "当信息足够时返回 {type:'proposal',summary:string,rules:<Game Rule DSL>}。"
            "只允许使用这个 DSL v0.1：" + json.dumps(DSL_SCHEMA_HINT, ensure_ascii=False)
            + "。不要生成代码，不要省略 deck、players、phases、actions。"
        )
