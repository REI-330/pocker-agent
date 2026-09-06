# 可执行 DSL v0.1 合约

- deck.ranks 从弱到强排列。标准牌 A 最大时为 2…10,J,Q,K,A。
- deck.suits 可以是自定义标签；S/H/D/C 和对应 Unicode 符号有内置开源牌面。无法匹配素材的自定义牌使用文字。
- phases 顺序执行。每阶段 max_turns 是所有玩家累计的动作次数上限。无人能执行时提前进入下一阶段，不能留下无按钮的活动状态。
- play/discard 从当前玩家手牌拿出 amount 张连续牌，card_index 指定起始位置。
- play 记录出牌者和桌面；discard 不参与已出牌最高牌比较。
- draw 从剩余牌堆摸 amount 张；pass 不变更牌。draw/pass 必须使用 system，play/discard 必须使用 hand。
- 最后阶段结束时结算本轮。highest_card 比较玩家本轮已出的最高牌（没有出牌时用手牌最高牌）；most_cards 比较轮末剩余手牌数量。并列者各得 points。
- scoring 为空时默认 highest_card、每轮 1 分。整局按累计总分定胜负；并列为平局。
- 轮末弃掉剩余手牌；下一轮从原牌堆继续发 starting_hand_size 张，不回收、不重洗。
- 达到 max_rounds 或牌堆不足以开始下一轮则结束，返回明确 finish_reason。
- 起始和回合转换后，状态必须满足 finished=true 或 legal_actions 非空。
- 模拟超过 max_steps 会报错，不伪造“完成”。
- 重复动作使用 revision 检查；过期提交返回 409，刷新牌局后再操作。
- 一轮允许多个阶段，单人试玩自动执行其他玩家，直到再次轮到玩家一或结束。

不支持任意自定义动作、下注、牌型、跟牌、特殊效果脚本。验证器 extra=forbid，不能靠额外 JSON 字段悄悄增加未实现的规则。
