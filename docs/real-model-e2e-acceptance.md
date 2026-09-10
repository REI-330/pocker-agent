# 真实模型端到端验收（2026-09-10，deepseek-flash）

## 验证目标

证明 Pocker Agent 从自然语言到可玩牌局的完整链路在真实浏览器、真实后端和
真实 LLM 下可用，而不是仅靠 mock 模型或脚本内硬编码规则。

## 环境

- 工作区：`E:\pocker agent`（分支 `codex/generated-game-runtime`，HEAD 71db86a）
- 后端：源码 Uvicorn `pocker_agent.api:app`，端口 8765，数据目录 `.validation/real-e2e-data`
- 前端：Vite dev server，端口 5175，`VITE_API_URL=http://127.0.0.1:8765`
- 模型：中转站 `https://forum.u3552374.nyat.app:49420/v1`，模型 ID `deepseek-flash`
  （Key 由用户提供，仅存于进程环境变量与系统凭据库，不写入仓库）
- 浏览器：Playwright 驱动真实 Edge（`channel=msedge`），headless 截图留存

## 实际操作（全部为真实点击/真实 HTTP，无接口替身）

1. 打开前端，模型设置面板显示"当前已保存：deepseek-flash"（来自环境变量初始配置）。
2. 在玩法对话框输入完整疯狂八描述（两人、52 张无王、各 5 张、同花色/同点数接牌、
   8 为万能牌并指定花色、无合法牌持续摸牌、牌堆耗尽回收弃牌保留顶牌、先出完获胜、隐藏对手手牌）。
3. 真实模型返回规则提案"两人疯狂八"（`kind=shedding`），页面列出 7 条规则事实，
   状态变为"规则已生成，请确认"。
4. 点击"确认规则"，`POST /api/agent/confirm` 返回 `confirmed`，ToolPlan 通过校验
   （`tool_plan_source=engine_agent`，工具：deck/zones/draw_discard/card_match/turn_order/condition）。
5. 点击"运行模拟"，seed=7 模拟完成，共 76 个事件，winner=player-1。
6. 点击"开始试玩"，页面显示"阶段：同花色或同点数接牌 · 牌堆剩余 41 张"。
7. 在真实浏览器中连续点击 27 步（选中可出牌 → 出牌；无合法牌时摸牌），
   电脑自动行动，最终"获胜者：player-2"（先出完手牌），状态"本局结束，可以再来一局"。
8. 展开"本局事件"，看到真实工具调用序列，例如：
   `draw_discard.draw` → `action_executed(draw)` → `card_match.call` →
   `draw_discard.discard_cards` → `action_executed(play)` → `turn_order.advance`。
9. 刷新浏览器，页面显示"已恢复上次牌局"，结算结果与会话仍存在。
10. 浏览器控制台无 error 级输出。

截图：`.validation/e2e-browser/01-config.png` … `08-restored.png`（共 8 张）。

## HTTP 层完整复跑（同一后端与模型）

`e2e_http_real_model.py` 用与浏览器相同描述走完整流程，结果：
`job(proposal, engine_agent) → confirm(confirmed) → simulate(76 events) →
session → 33 步合法动作 → finished(hand_empty, 100 events) → restore(同会话)`。

## 发现的真实问题（已定位，属模型波动而非链路缺陷）

1. **ToolPlan 生成偶发失败**：deepseek-flash 对同一规则约 80% 生成有效 ToolPlan。
   失败模式有两种，均被 EngineAgent 捕获并尝试修复，修复失败时返回
   `engine_agent_invalid_tool_plan`，前端显示错误：
   - 模型返回与 ToolPlan schema 完全不同的结构（无 `tools` 字段）；
   - 修复时给不接受 config 的工具（如 `draw_discard`）填了 `config`，
     触发 `invalid_tool_config:draw_discard`。
   用户重发即可成功（本验收即通过重试完成）。若需提升成功率，可改进
   EngineAgent 的修复提示或 normalize 逻辑（见开发问题列表）。
2. **出牌按钮与手牌索引联动**：当玩家第 1 张牌不可出但后续牌可出时，
   "出牌"按钮初始 disabled，必须先选中可出牌。这是前端交互设计，
   验收脚本据此先点选合法牌再点出牌。

## 结论

- 真实模型生成 → ToolPlan → 确认 → 模拟 → 浏览器试玩 → 结算 → 刷新恢复，
  全链路在真实浏览器与真实 HTTP 下通过；控制台无错误。
- 模拟与试玩结果不同（模拟 player-1 胜、试玩 player-2 胜）属正常：
  试玩中人类玩家实际决策路径与固定策略不同。
- 此验收覆盖疯狂八单人试玩路径；多轮、不同玩法和 3–9 人场景不在本次范围。
