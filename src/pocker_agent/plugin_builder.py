"""Model writes programs; the host fixes tests before repair and gates execution."""

import json
from collections import Counter
from copy import deepcopy
from functools import lru_cache

from .llm import OpenAICompatibleClient
from .model_json import parse_object
from .plugin_sandbox import verify_plugin, verify_plugin_report
from .plugin_schema import PluginPlan, PluginRule, PluginState, card_catalog

PROTOCOL = """
你正在编写受限环境里的真实 JavaScript 游戏逻辑，不是选择预设游戏模板。
源码是一个返回对象的JavaScript表达式，例如 (() => { /* helpers */ return {setup, actions, step}; })()。
禁止markdown源码围栏、import、export、require、fetch、文件、网络、Date、Math.random、异步。
只有三个同步函数：
setup(deck, playerCount, cards) -> state。deck是宿主已洗牌的ID数组；cards是ID到{rank,suit,value}的字典。
actions(state, cards) -> [{id,label,target_player?,card_index?}]。每个id唯一，只列合法动作。
id只能使用英文、数字、下划线、冒号、短横线，最多64字符；必须与固定测试action_id完全一致。
step(state, action, cards) -> 新state。action是actions返回的对象。
所有状态必须放在state中，每次调用都是全新VM，不能依赖闭包变量保存牌局。
state严格且仅有：hands(各玩家牌ID数组), deck(剩余牌ID), discard(已移除牌ID),
current_player(0起算), finished(bool), winners(玩家下标数组), scores(数字数组), phase(中文), data(扩展JSON对象)。
所有牌必须始终恰好存在于hands/deck/discard之一；消除牌移动到discard。禁止创造牌或丢牌。
未结束winners=[]且至少有一个合法动作；结束winners非空、actions=[]。
所有源码函数都必须支持下文固定测试中的局部牌局，不能要求牌组总是满52张。
只提供通用牌桌和合法动作按钮，不执行生成的HTML/浏览器JS。点击隐藏牌时，
action用target_player和card_index表示位置；id/label只能含位置，不能透露隐藏牌值。
自己的手牌显示牌面，对手始终显示牌背；结束条件以用户规则为准。
仅当用户规则要求某玩家退出后其他人仍继续（例如三人游戏剩两人）才需要观看推进动作。
主持人自动操作其他玩家，从actions中选一个；不要用只有完整牌面信息才有意义的动作标签。
需要抽隐藏牌的游戏：每次被抽牌后将剩余目标手牌做确定性位置扰动（可用state.data中的PRNG状态），
避免玩家长期跟踪旧位置。允许在源码里实现确定性PRNG，不允许Math.random。
实现用户完整的规则；不能用少量牌或缩短轮次偷偷简化。
"""

PLAN_PROMPT = (
    PROTOCOL
    + """
先制定行为合约和至少3个独立的规则测试，不要写源码。输出json：
{"type":"plan","plan":<PluginPlan>}；有实质缺失则输出{"type":"question","question":"..."}。
如果用户明确要求只修正文案、保持原源码及行为测试，可返回{"type":"plan","reuse_source":true,"plan":<PluginPlan>}。
复用时只能修改title/description/requirements；其余所有字段包括game_id、scenarios、max_steps必须完整沿用旧程序。
玩法机制或行为测试需要修改时不得使用reuse_source，仍须编写源码。
真的超出上述运行协议则输出{"type":"unsupported","message":"具体原因"}。
requirements完整复述用户确定的规则，每项一条；不能为了实现方便改变配对/抽牌/出局/胜负条件。
scenarios是小牌局单步测试，先确定合法action_id，再明确expected的state字段路径和值。
字段路径使用hands.0这样的点分写法，不使用hands[0]。逐张手算抽牌、配对后的结果，再写expected。
即使只用局部牌局，也必须满足测试声称的结束条件：若规则要求仅剩一张，剩两张时不能断言结束。
至少分别覆盖核心动作、回合转换和终局判定。牌ID=rank+suit，比如AS、2H、QD。
测试必须只使用未被excluded_cards移除的牌。移除的牌不可能作为最后留在手里的牌。
测试state可只放少量合法牌，无需填充整副牌。配对规则需设计能区分同点和同色等变体的反例。
expected只断言该测试必需的字段；不要固定洗牌后的手牌顺序或无关phase文案。
每个消除动作必须满足用户的配对条件，不同点数不能假设消除。两人游戏中如果一人空手且另一人只剩一张，必须按用户终局规则结束。
玩家初始手牌由源码发牌，所以players.starting_hand_size=0，min/max为同一实际人数。
仅输出json，不要自称已运行测试。
PluginPlan JSON Schema:
"""
    + json.dumps(PluginPlan.model_json_schema(), ensure_ascii=False)
)


@lru_cache(maxsize=32)
def accepted_program(serialized):
    return verify_plugin(PluginRule.model_validate_json(serialized))


def validate_scenarios(plan):
    available = card_catalog(plan)
    for scenario in plan.scenarios:
        state = scenario.state.model_dump(mode="json")
        cards = (
            state["deck"] + state["discard"] + [c for h in state["hands"] for c in h]
        )
        if len(cards) != len(set(cards)) or not set(cards) <= available.keys():
            raise ValueError(f"{scenario.name}: 测试使用了不存在、被排除或重复的牌")
        after = deepcopy(state)
        asserted_zones = {}
        for path, expected in scenario.expected.items():
            if path in {"deck", "discard"}:
                asserted_zones[path] = expected
            elif path == "hands":
                asserted_zones.update(
                    {f"hands.{i}": hand for i, hand in enumerate(expected)}
                )
            elif path.startswith("hands.") and len(path.split(".")) == 2:
                asserted_zones[path] = expected
            parts = path.split(".")
            parent = after
            for part in parts[:-1]:
                parent = parent[int(part)] if isinstance(parent, list) else parent[part]
            parent[int(parts[-1]) if isinstance(parent, list) else parts[-1]] = expected
        parsed = PluginState.model_validate(after)
        asserted_cards = [card for zone in asserted_zones.values() for card in zone]
        if len(asserted_cards) != len(set(asserted_cards)) or not set(
            asserted_cards
        ) <= set(cards):
            raise ValueError(
                f"{scenario.name}: 测试预期在多个牌区重复同一张牌或创造新牌；抽出的牌必须从原手牌移除"
            )
        if all(k in scenario.expected for k in ("hands", "discard", "deck")):
            resulting = (
                parsed.deck + parsed.discard + [c for h in parsed.hands for c in h]
            )
            if Counter(cards) != Counter(resulting):
                raise ValueError(f"{scenario.name}: 测试预期凭空创造或丢失了牌")


def build_program(model, conversation, previous=None, progress=lambda message: None):
    if isinstance(model, OpenAICompatibleClient):
        model.streaming = True
        model.reasoning_effort = model.reasoning_effort or "low"
        model.max_tokens = 12000
        model.on_notice = progress
        model.on_progress = lambda size: progress(f"正在接收模型输出：{size} 字符")
    progress("制定规则合约和行为测试")
    messages = [{"role": "system", "content": PLAN_PROMPT}, *conversation]
    if previous:
        messages.append(
            {
                "role": "user",
                "content": "需按最新要求修改的旧程序："
                + json.dumps(previous, ensure_ascii=False),
            }
        )
    for planning_attempt in range(3):
        raw_plan = model.complete(messages)
        try:
            plan_result = parse_object(raw_plan)
            if plan_result.get("type") in {"question", "unsupported"}:
                return plan_result, []
            plan = PluginPlan.model_validate(plan_result.get("plan", plan_result))
            validate_scenarios(plan)
            if plan_result.get("reuse_source") is True:
                if not previous:
                    raise ValueError("没有可复用的原程序")
                original = PluginRule.model_validate(previous)
                metadata = {"title", "description", "requirements"}
                if original.model_dump(
                    exclude=metadata | {"source", "kind", "schema_version"}
                ) != plan.model_dump(exclude=metadata):
                    raise ValueError(
                        "复用源码时只能修改说明；必须保留全部原执行字段和固定测试，否则请取消reuse_source并编写新逻辑"
                    )
            break
        except (RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
            if planning_attempt == 2:
                raise ValueError("生成的行为合约无效：" + str(error)[:2000]) from error
            progress("行为测试存在结构矛盾，重新制定合约：" + str(error)[:180])
            messages.extend(
                [
                    {"role": "assistant", "content": raw_plan},
                    {
                        "role": "user",
                        "content": "先修正规则合约和测试，保留最初用户规则。错误："
                        + str(error)[:2000],
                    },
                ]
            )
    if plan_result.get("reuse_source") is True:
        progress("仅修正说明，复用原源码并重新验证固定测试与完整对局")
        rule = PluginRule(**plan.model_dump(), source=original.source)
        report = verify_plugin_report(rule)
        return {"type": "proposal", "rules": rule}, [
            {"attempt": 1, "status": "passed", "reused_source": True, "checks": report["checks"], "verification": report}
        ]
    prompt = [
        {
            "role": "system",
            "content": PROTOCOL + '\n只返回json {"source":"完整JavaScript表达式"}。',
        },
        {
            "role": "user",
            "content": json.dumps(plan.model_dump(mode="json"), ensure_ascii=False),
        },
        {
            "role": "user",
            "content": "原始用户要求（实现必须同时满足）："
            + json.dumps(conversation, ensure_ascii=False),
        },
    ]
    attempts = []
    for attempt in range(3):
        progress(
            "编写游戏代码"
            if not attempt
            else f"根据测试错误修复代码（第 {attempt} 次）"
        )
        raw = model.complete(prompt)
        try:
            source = parse_object(raw)["source"]
            rule = PluginRule(**plan.model_dump(), source=source)
            progress("执行固定行为测试、三组完整对局和确定性重放")
            report = verify_plugin_report(rule)
            attempts.append(
                {"attempt": attempt + 1, "status": "passed", "checks": report["checks"], "verification": report}
            )
            return {"type": "proposal", "rules": rule}, attempts
        except (RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
            detail = str(error)[:2500]
            attempts.append(
                {"attempt": attempt + 1, "status": "failed", "error": detail}
            )
            progress("测试失败，正在整理修复反馈：" + detail[:180])
            prompt.extend(
                [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": "测试失败："
                        + detail
                        + "。保持原合约和固定测试，只修复源码，返回完整source json。",
                    },
                ]
            )
    return {
        "type": "error",
        "message": "代码生成后未通过测试，未发布可玩版本。",
        "errors": [a["error"] for a in attempts],
    }, attempts
