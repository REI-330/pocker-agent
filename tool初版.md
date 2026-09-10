# 常见扑克牌玩法与通用 Tool 调研

## 目的

把常见玩法拆成可复用的规则机制，确定 Agent 工具箱应提供哪些原子能力，避免每种玩法都重新编写一个 Engine。

## 玩法机制分类

| 类别 | 代表玩法 | 核心机制 |
|---|---|---|
| 比较/摊牌 | War、五张牌、百家乐 | 发牌、点数或牌型比较、结算 |
| 接牌/出完 | Crazy Eights、UNO 类、接龙变体 | 顶牌、匹配条件、万能牌、摸牌、出完结束 |
| 爬牌 | 斗地主、Big Two、President | 多牌型、压过上家、过牌、重新领出 |
| 墩牌 | Hearts、Spades、Bridge、Whist | 跟花色、王牌、墩胜者、竞叫、队伍 |
| 组合/Meld | Rummy、Gin Rummy、Canasta | 集合、顺子、摸弃牌、组合计分 |
| 隐藏信息/交换 | Go Fish、Old Maid、Kemps | 指定玩家询问、抽取隐藏牌、成组、配对 |
| 下注/银行 | Texas Hold'em、Omaha、Blackjack、Baccarat | 下注、奖池、阶段、庄家规则、赔率 |
| 布局/耐心 | Klondike、FreeCell、Pyramid | 多牌区、可见性、合法移动、目标区 |

## 建议的通用 Tool 分层

### 1. Card Space

- `deck.create`：建立牌组和牌面属性
- `deck.shuffle`：确定性洗牌
- `zone.create`：牌库、手牌、弃牌堆、公共牌、目标区
- `card.move`：牌在牌区间移动
- `card.draw` / `card.deal`：抽牌和发牌
- `card.reveal` / `card.hide`：控制可见性
- `card.return`：回收、重洗、重置

### 2. Selection and legality

- `select.cards`：从指定牌区选择一张或多张
- `select.player`：指定其他玩家
- `rule.match`：按花色、点数、颜色或自定义属性匹配
- `rule.follow_suit`：跟花色约束
- `rule.can_play`：检查动作是否合法
- `rule.must_respond`：有合法响应时禁止过牌

### 3. Combinations and comparison

- `hand.group`：按点数/花色分组
- `meld.detect`：集合、顺子、同花组合
- `hand.rank`：通用牌型排序
- `hand.compare`：同类牌型比较
- `trick.resolve`：一墩牌的赢家判断
- `climb.beats`：爬牌玩法压牌判断

### 4. Turn and phase

- `turn.order`：顺时针、逆时针、指定顺序
- `turn.skip`：跳过玩家
- `turn.reverse`：反转方向
- `turn.pass`：过牌与连续过牌计数
- `phase.start` / `phase.advance`：阶段推进
- `trigger.emit`：动作后的事件触发

### 5. Resources and settlement

- `ledger.commit`：积分或筹码提交
- `pot.build`：主池、边池、退款
- `pot.distribute`：按资格、排名、奇数筹码分配
- `score.add` / `score.subtract`：积分变化
- `payout.odds`：赔率和庄家赔付
- `team.split`：队伍与合作方收益

### 6. End conditions

- `condition.hand_empty`
- `condition.deck_empty`
- `condition.target_score`
- `condition.all_folded`
- `condition.last_trick`
- `condition.no_legal_action`

## 当前项目覆盖情况

已实现：牌堆、德州牌型、斗地主牌型、下注池、斗地主结算、基础回合配置，以及斗地主/德州专用 Engine。

仍不足：完整跟花色/墩牌、Meld 识别与计分、隐藏信息交换、通用触发器、声明式结束条件、真正可执行的 `turn_order` 和 `arithmetic_solver`。

## 架构建议

Agent 应输出声明式 `RulePlan`，内容包括牌区、状态变量、动作、合法性条件、触发器、阶段和结束条件。`Game Layer` 负责把计划连接到 Tool Registry；通用执行器负责状态迁移；专用 Engine 只保留无法由现有 Tool 表达的机制。

## 主要来源

- [Pagat 分类索引](https://www.pagat.com/class/)
- [Pagat 墩牌类玩法](https://www.pagat.com/class/trick.html)
- [Pagat 组合牌型类玩法](https://www.pagat.com/class/combine.html)
- [Pagat Rummy 规则](https://www.pagat.com/rummy/rummy.html)
- [Pagat Poker 规则](https://www.pagat.com/poker/rules.html)
- [Pagat Baccarat 规则](https://www.pagat.com/banking/baccarat.html)
- [Bicycle 纸牌玩法索引](https://bicyclecards.com/how-to-play/)
