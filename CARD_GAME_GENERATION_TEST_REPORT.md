# Pocker Agent：10 种常见扑克牌玩法生成测试报告

测试日期：2026-09-09

## 测试目标

验证 Agent 是否能把常见扑克牌玩法转换为受限 DSL、Tool Plan 和可执行 Engine，并区分已有能力、可组合能力和缺少 Engine 的玩法。规则选择参考 [Pagat 分类索引](https://www.pagat.com/alpha/)、[Poker rules](https://www.pagat.com/poker/rules/)、[Baccarat rules](https://www.pagat.com/banking/baccarat.html) 及 [Go Fish](https://en.wikipedia.org/wiki/Go_Fish)。

## 测试方法

每个玩法包含标准规则描述、人数、牌堆、核心动作和胜负条件。测试链路为：

`自然语言 → Agent → DSL 校验 → Tool Plan → Game Layer → Engine setup/simulation`

工具调用采用注册表查找，而不是让模型输出任意代码：

- 牌堆：`DeckTool`
- 牌型：`hand_rank`、`doudizhu_hand_rank`
- 下注：`PotTool`
- 顺序：`turn_order`（当前为占位能力）
- 玩法专用逻辑：斗地主 `DoudizhuEngine`、德州 `HoldemEngine`

## 10 个玩法结果

| # | 玩法 | 关键机制 | 本地合约/Engine结果 | 结论 |
|---:|---|---|---|---|
| 1 | 红心大战 Hearts | 4人、跟花色、红心罚分、黑桃Q罚分 | 无 Hearts DSL/Engine；不能启动 | 失败：缺少 trick-taking 与罚分 Engine |
| 2 | 黑桃 Spades | 4人组队、竞叫、黑桃王牌、按墩结算 | 无 Spades DSL/Engine；不能启动 | 失败：缺少竞叫、组队、墩牌 Engine |
| 3 | 基础拉密 Rummy | 摸牌、弃牌、集合/顺子、先出完 | 无 Rummy DSL/Engine | 失败：缺少 meld、摸弃牌和结束判定 |
| 4 | Gin Rummy | 2人、摸弃牌、敲牌、deadwood 计分 | 无 Gin DSL/Engine | 失败：缺少敲牌和 deadwood 计分 |
| 5 | Go Fish | 2–5人、询问点数、摸牌、四张成组 | 无询问/指定玩家动作 DSL/Engine | 失败：缺少隐藏信息询问机制 |
| 6 | Crazy Eights | 2–6人、按花色/点数接牌、8万能 | 已有 `shedding` Engine 可表达基础接牌；人数上限当前为4 | 部分通过：需扩展人数与万能牌动作校验 |
| 7 | War | 2人、同时翻牌、平局加牌、收集全部牌 | 无专用 War Engine；旧版阶段 DSL 不能表达平局加牌 | 失败：需要新 Engine |
| 8 | Old Maid | 3–6人、抽下家手牌、弃对子、剩余Q输 | 无抽取他人隐藏手牌 DSL/Engine | 失败：缺少隐藏手牌抽取 |
| 9 | Big Two/锄大D | 4人、爬牌、单/对/三/五张、2最大 | 可复用斗地主部分牌型工具；无 Big Two 出牌与计分 Engine | 部分通过：不能安全复用斗地主 Engine |
| 10 | Baccarat | 闲/庄、固定补牌表、点数个位、下注 | 无 Baccarat DSL/Engine；`PotTool` 只提供账本 | 失败：缺少固定补牌表与庄闲结算 Engine |

## 真实模型调用结果

已使用当前配置的兼容 Chat Completions 服务尝试串行提交 10 个完整玩法描述。服务端在首批请求上持续超过可接受观察窗口，未返回可解析结果，随后停止该批任务；因此本报告不把这批请求标记为“生成成功”或“生成失败”。这暴露了真实验收的一个独立问题：批量玩法生成需要请求级超时、重试和作业状态展示。

## Agent 如何调用 Tool 构建游戏

1. Agent 从规则文本识别玩法族并要求补全人数、牌组、动作和结算信息。
2. 模型返回 DSL proposal；`validate_dsl` 拒绝未知字段、非法牌组和缺失机制。
3. `plan_for_rules` 生成工具计划，例如德州：`deck → pot → hand_rank`；斗地主：`deck → doudizhu_hand_rank → turn_order → settlement`。
4. `GameLayer.from_plan` 从 `ToolRegistry` 实例化工具，未知工具名直接失败。
5. `create_engine` 只选择已注册 Engine；Engine 在确定性运行中调用工具并产生事件。
6. runtime 保存 Engine 序列化快照，恢复时重建同一规则、工具和状态。

模型不能通过这条链路临时写入任意 JavaScript 来绕过校验。对于没有专用 Engine 的玩法，正确结果应是缺少能力或进入独立 Engine 开发，而不是伪装成“比大小”。

## 结论与下一批开发建议

10 个玩法中，当前可直接完整执行的是已实现的斗地主/德州扑克及既有基础接牌协议；Crazy Eights 只能部分复用。其余玩法需要新增专用 Engine，尤其是：

- trick-taking 基础（跟牌、墩、王牌、竞叫、队伍）
- meld 基础（集合、顺子、摸牌、弃牌、deadwood）
- 隐藏信息动作（询问、抽取指定玩家手牌）
- 固定流程庄家游戏（补牌表、庄闲结算）

本轮真实模型批量请求未形成有效返回，后续应先增加异步 jobs、单请求超时和结构化输出重试，再进行 10 个玩法的真实生成回归。
