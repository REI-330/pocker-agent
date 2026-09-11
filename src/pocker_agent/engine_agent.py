from __future__ import annotations

import json
from typing import Any

from .llm import ModelClient
from .model_json import parse_object
from .game_rules import PlayableRule
from .tools.plan import ToolPlan
from .tools.plans import plan_for_rules
from .tools.registry import default_registry
from .game_layer import GameLayer


class EngineAgent:
    """Compile confirmed rules into a reviewable ToolPlan.

    The model may choose and configure tools, but the host validates the plan
    against the registry.  A family-specific game is never silently replaced
    by a host-generated plan: an invalid model response is an explicit error.
    """

    def __init__(self, model: ModelClient):
        self.model = model

    def compose(self, rules: PlayableRule) -> tuple[dict[str, Any], str]:
        # The legacy DSL has no family-specific tool contract. Keep its
        # established single model turn and use the compatibility compiler.
        if not getattr(rules, "kind", None):
            return plan_for_rules(rules), "host_compatibility_compiler"
        prompt = {
            "role": "user",
            "content": ("根据已确认规则生成 ToolPlan，只返回 JSON。严格遵守下面的字段形状，不要自行发明 schema："
                       "players 必须是整数；tools 必须是 [{name:string,config:object}]；actions 必须是 "
                       "[{tool:string,operation:string,args:object,result_key?:string}]；phases 必须是字符串数组；"
                       "end_conditions 必须是字符串数组。不要使用 phases 对象、tool_invocations、action、params 或 allowed_actions。"
                       "actions 仅是组装预检动作，不能伪称已表达完整回合流程。工具配置必须与规则一致。"
                       "该规则需要的最小工具集合：" + ",".join(sorted(self.required_tools(rules))) + "。"
                       "工具配置参考（供你生成计划，宿主不会自动补全缺失工具）："
                       + json.dumps(plan_for_rules(rules)["tools"], ensure_ascii=False) + "。"
                       "只能使用以下真实 operation：deck.cards()、deck.shuffled(seed)、deck.deal(seed,hands,cards_each,kitty)、"
                       "deck.deal_into(stock,hands,cards_each)、deck.draw(stock,hand,count)；"
                       "hand_rank.evaluate(cards)；arithmetic_solver.solve(numbers)、arithmetic_solver.validate(expression,numbers)；"
                       "draw_discard.draw(hand,count,recycle,recycle_seed)、draw_discard.discard_cards(hand,cards)；"
                       "turn_order.advance(steps)；card_match.call(card,top,active_suit,wild_ranks)。"
                       "禁止写 deck.create、deck.shuffle、deck.draw(deck=...) 或不存在的 operation。"
                       "只能使用这些工具：" + ", ".join(default_registry().names()) + "。规则："
                       + ("所有内置牌类玩法必须返回完整 flow（entry、initial、nodes）。call 节点使用 action 和 next，"
                          "branch 使用 value、cases:[{value,target}] 和默认 next；wait 使用 inputs:{动作:目标节点}；end 只可在 finished=true 后执行。"
                          "用 logic.evaluate 的 all/any/eq/ge/lt/count/add/join 表达判断和轮次；用 deck.draw 表达庄家要牌循环。"
                          "不要用专用 Engine 或省略 natural、软17规则、平局、max_rounds。参考组合供生成和修改："
                          + json.dumps(plan_for_rules(rules), ensure_ascii=False)
                          if getattr(rules, "kind", "") in {"arithmetic", "blackjack", "shedding", "doudizhu", "holdem"} else "")
                       + json.dumps(rules.model_dump(mode="json"), ensure_ascii=False)),
        }
        messages = [{"role": "system", "content": "你是游戏引擎 Agent，只能编排已注册的确定性 Tool，不得写代码。"}, prompt]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                raw = self.model.complete(messages)
                value = parse_object(raw)
                candidate = value.get("tool_plan", value)
                source = "engine_agent"
                try:
                    plan = ToolPlan.model_validate(candidate)
                except Exception:
                    # Some OpenAI-compatible gateways follow their own
                    # workflow schema (phase objects and tool invocation
                    # objects) even after being asked for our compact DSL.
                    # Preserve the model's selected tool names while lowering
                    # that representation into the reviewed ToolPlan; random
                    # or non-object responses still fail below.
                    candidate = self._normalize_gateway_plan(candidate, rules)
                    plan = ToolPlan.model_validate(candidate)
                    source = "engine_agent_normalized"
                if plan.game_kind != getattr(rules, "kind", "legacy"):
                    raise ValueError("tool_plan_game_kind_mismatch")
                if getattr(rules, "kind", "") in {"arithmetic", "blackjack", "shedding", "doudizhu", "holdem"} and plan.flow is None and source == "engine_agent":
                    raise ValueError("tool_plan_flow_required:" + rules.kind)
                known = set(default_registry().names())
                if any(item.name not in known for item in plan.tools):
                    raise ValueError("tool_plan_unknown_tool")
                missing = self.required_tools(rules) - {item.name for item in plan.tools}
                if missing:
                    raise ValueError("tool_plan_missing_required:" + ",".join(sorted(missing)))
                if not rules.players.min_players <= plan.players <= rules.players.max_players:
                    raise ValueError("tool_plan_player_count_mismatch")
                GameLayer.from_plan(plan)
                return plan.model_dump(mode="json"), source
            except Exception as error:
                last_error = error
                if attempt == 0:
                    messages.append({"role": "user", "content":
                        "上一份响应无效（" + str(error) + "）。请立即修正，只返回完整 ToolPlan JSON，不能返回解释、Markdown 或代码。"})
                    messages.append({"role": "user", "content":
                        "请优先复制下面这个同类玩法的已注册工具配置骨架，只修改与你确认规则不一致的参数；不要新增工具、不要删掉最小工具，也不要为牌局回合发明 operation："
                        + json.dumps(plan_for_rules(rules), ensure_ascii=False)})
        raise ValueError("engine_agent_invalid_tool_plan") from last_error


    @staticmethod
    def required_tools(rules: PlayableRule) -> set[str]:
        """Minimum capabilities needed by the deterministic runtime for a family."""
        return {
            "arithmetic": {"deck", "arithmetic_deal", "arithmetic_solver", "state", "score_settle"},
            "blackjack": {"deck", "hand_rank", "state", "logic", "point_contest", "score_settle", "winner_resolve"},
            "shedding": {"deck", "draw_discard", "card_match", "turn_order"},
            "doudizhu": {"deck", "doudizhu_hand_rank", "climb_beats", "turn_order", "doudizhu_turn", "state"},
            "holdem": {"deck", "betting_round", "phase_progress", "community_deal", "all_in", "showdown", "settle_pots", "pot_winners", "state"},
        }.get(getattr(rules, "kind", ""), {"deck"})

    @staticmethod
    def _normalize_gateway_plan(candidate: Any, rules: PlayableRule) -> dict[str, Any]:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("tools"), list):
            raise ValueError("unsupported_gateway_tool_plan")
        known = set(default_registry().names())
        names: list[str] = []
        configs: dict[str, dict[str, Any]] = {}
        for item in candidate["tools"]:
            name, config = (item, {}) if isinstance(item, str) else (item.get("name", item.get("tool")), item.get("config", {})) if isinstance(item, dict) else (None, {})
            if not isinstance(name, str) or name not in known:
                raise ValueError("tool_plan_unknown_tool")
            if name in names or not isinstance(config, dict):
                raise ValueError("invalid_gateway_tool_config")
            names.append(name)
            configs[name] = config
        if not names:
            raise ValueError("unsupported_gateway_tool_plan")
        # Normalize shape only. Never invent tools, config or executable actions.
        phases = [p if isinstance(p, str) else p.get("name") for p in candidate.get("phases", [])]
        end_conditions = [c if isinstance(c, str) else c.get("condition") for c in candidate.get("end_conditions", [])]
        return {**candidate, "schema_version": candidate.get("schema_version", "1.0"),
                "players": candidate["players"]["max_players"] if isinstance(candidate.get("players"), dict) else candidate.get("players"),
                "tools": [{"name": name, "config": configs.get(name, {})} for name in names],
                "actions": candidate.get("actions", []), "phases": phases,
                "end_conditions": end_conditions}
