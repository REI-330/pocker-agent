# ToolPlan Runtime 重构说明

## 目标

把“玩法生成”和“牌局执行”分开：

```text
自然语言 → RuleAgent → EngineAgent → ToolPlan
                                      ↓
                              ToolPlanRuntime
                                      ↓
                         确定性牌局状态与事件
```

Agent 只负责理解规则和编排已注册工具。`ToolPlanRuntime` 负责校验计划、配置工具、执行计划声明的初始化动作、启动确定性牌局、验证运行期间的 `tool_called` 事件，并把同一份计划和事件持久化到运行会话。

## 代码边界

- `src/pocker_agent/engine_agent.py`：模型生成 `ToolPlan`，检查工具是否已注册。
- `src/pocker_agent/game_layer.py`：按计划实例化工具并执行声明动作。
- `src/pocker_agent/runtime.py`：新增 `ToolPlanRuntime`，负责计划生命周期和白名单校验。
- `src/pocker_agent/family_engines.py`、`doudizhu_engine.py`、`holdem_engine.py`：确定性玩法执行器通过统一的 `tool_call` 记录工具事件；如果计划缺少运行所需工具，动作会失败并返回 `tool_not_declared:<tool>`。
- `src/pocker_agent/api.py`：确认阶段校验计划的玩法类型和最小工具集合；运行会话返回 `tool_plan_source`、`tool_plan`、`tool_events` 和编译期 `composition_events`。

`tool_events` 只包含真实牌局执行期间的调用。计划编译/预执行产生的事件放在 `composition_events`，避免把编译期发牌误报成牌局中的第二次发牌。

## 兼容边界

直接调用 `RuntimeStore.create()` 且没有传入计划时仍会使用 `host_compatibility_compiler`，用于旧版模拟和导出流程。前端正常生成流程会把 `/api/agent/turn` 返回的 Agent 计划传入 `/api/runtime/sessions`，运行结果中的 `tool_plan_source` 为 `agent`。计划不完整时不会偷偷切换到另一套玩法；执行到缺失工具的动作会失败。

## 验证

- `uv run pytest -q`：166 passed。
- `uv run python scripts/validate_agent_tool_chain.py`：真实 HTTP 模型协议 + FastAPI 运行链，疯狂八的规则由模型返回，ToolPlan 含 `deck/zones/draw_discard/card_match/turn_order`，运行会话保存同一计划，运行期真实发牌事件为 `deck.deal`。
- `uv run python scripts/validate_holdem_agent_runtime.py`：启动源代码 Uvicorn，通过真实 HTTP 完成模型 → ToolPlan → 德州运行时，执行四个动作并完成五张公共牌；验证 `betting_round`、`community_deal`、`showdown`、`settle_pots` 等声明工具均出现在真实事件轨迹中。

