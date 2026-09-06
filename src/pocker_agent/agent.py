from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .llm import ModelClient
from .models import GameRuleDSL
from .validation import validate_dsl

CONTRACT = """
你是 Pocker Agent 的规则设计助手，只返回有效 json 对象。
这是有限的纸牌 DSL demo；不能假装支持 DSL 未表达的规则。
支持：按顺序执行阶段，play/discard/draw/pass，按轮计分和有限轮数。
不支持：扑克下注、任意出牌组合、花色跟牌、比较上一手牌、交换牌、特殊牌效果、隐藏规则脚本。
用户要求不支持的规则时，返回 question 说明限制，请用户决定是否改成可支持的规则，不可擅自删减。
缺少胜负、玩家数、初始手牌、轮数、牌强度等重要信息时，用一次简短 question 集中澄清。
question 格式：{"type":"question","question":"...","missing":["..."]}。
信息完整时：{"type":"proposal","summary":"中文准确复述所有规则","rules":<DSL>}。
执行语义：
deck.ranks 按从小到大排列，例如 2,3,4,5,6,7,8,9,10,J,Q,K,A。suits 推荐 S,H,D,C。
每个阶段 max_turns 是所有玩家合计动作次数；阶段结束进入下一阶段，最后阶段结束结算本轮。
每轮开始从剩余牌堆给每人发 starting_hand_size 张牌；轮末手牌弃置，不洗回牌堆。
牌堆不足以再次发牌时提前结束，必须向用户说明，或选择充足牌组。
play/discard 使用 hand，draw/pass 使用 system；amount 是动作处理张数，pass 设 amount=0。
play 记录桌面和出牌者；discard 弃牌不参与本轮最高牌比较。
scoring.highest_card 比较本轮各玩家已出的最高牌（没出过则用手牌最高牌），并列者各得 points。
scoring.most_cards 比较轮末手牌数量，并列者各得 points。scoring 为空等同最高牌每轮1分。
max_rounds 后总分最高者获胜，并列为平局。电脑玩家自动选择第一个合法动作。
你必须用这些语义准确表达用户规则。摘要说明阶段、牌点顺序、平局和轮末处理。
不要生成代码。修正规则时保留用户已经确定的规则。
"""


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

    def turn(self, session, user_text):
        session.messages.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": self._system_prompt()}]
        if session.proposal:
            messages.append({"role": "user", "content": "当前规则草案：" + json.dumps(session.proposal, ensure_ascii=False)})
        raw = self.model.complete(messages + session.messages, response_format={"type": "json_object"})
        result = self._parse_json(raw)
        if result.get("type") == "question":
            question = result.get("question")
            if not isinstance(question, str) or not question.strip():
                raise RuntimeError("model_question_empty")
            session.messages.append({"role": "assistant", "content": question})
            missing = result.get("missing", [])
            return AgentTurn("question", question, missing=missing if isinstance(missing, list) else [])
        proposal = result.get("rules", result)
        if not isinstance(proposal, dict):
            return AgentTurn("error", "模型没有返回可解析的规则对象。", errors=["model_output_not_object"])
        rules, errors = validate_dsl(proposal)
        if errors:
            repair, repair_error = self._repair(proposal, errors)
            if repair is not None:
                rules, errors = validate_dsl(repair)
            elif repair_error:
                errors.append(repair_error)
        if errors:
            return AgentTurn("error", "规则未通过执行校验，请修改。", errors=errors)
        session.proposal = rules.model_dump(mode="json")
        summary = str(result.get("summary", "规则已生成，请核对后确认。"))
        session.messages.append({"role": "assistant", "content": json.dumps({"summary": summary, "rules": session.proposal}, ensure_ascii=False)})
        return AgentTurn("proposal", summary, rules)

    def confirm(self, session):
        if not session.proposal:
            return AgentTurn("error", "还没有可以确认的规则。", errors=["proposal_missing"])
        rules, errors = validate_dsl(session.proposal)
        if errors:
            return AgentTurn("error", "规则仍未通过校验。", errors=errors)
        session.confirmed = True
        return AgentTurn("confirmed", "规则已确认，可以开始模拟。", rules)

    def _repair(self, proposal, errors):
        try:
            raw = self.model.complete([
                {"role": "system", "content": self._system_prompt() + "修复下列 DSL 的结构错误，只返回 rules json 对象，保持用户规则含义。"},
                {"role": "user", "content": json.dumps({"rules": proposal, "errors": errors}, ensure_ascii=False)},
            ], response_format={"type": "json_object"})
            repaired = self._parse_json(raw)
            candidate = repaired.get("rules", repaired)
            return (candidate, None) if isinstance(candidate, dict) else (None, "repair_output_not_object")
        except RuntimeError as error:
            return None, f"repair_failed:{error}"

    @staticmethod
    def _parse_json(raw):
        if not isinstance(raw, str):
            raise RuntimeError("model_output_not_text")
        text = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
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
    def _system_prompt():
        return CONTRACT + "\nDSL JSON Schema:\n" + json.dumps(GameRuleDSL.model_json_schema(), ensure_ascii=False)
