import type { RuleAction } from "../../api.js";
import type { DecisionContext } from "../types.js";

/**
 * Bot策略接口 - 可插拔的决策算法
 */
export interface BotStrategy {
  readonly name: string;
  
  /**
   * 从合法动作中选择一个
   * @param context 决策上下文
   * @returns 选中的动作
   */
  selectAction(context: DecisionContext): RuleAction | Promise<RuleAction>;
}
