import type { RuleAction } from "../../api.js";
import type { BotStrategy } from "./bot-strategy.js";
import type { DecisionContext } from "../types.js";

/**
 * 贪婪策略 - 优先选择可能带来最大收益的动作
 * 简单实现：优先选择约束条件最多的动作（通常是更复杂的动作）
 */
export class GreedyStrategy implements BotStrategy {
  readonly name = "Greedy";
  
  selectAction(context: DecisionContext): RuleAction {
    const { legalActions } = context;
    if (legalActions.length === 0) {
      throw new Error("No legal actions available");
    }
    
    // 选择约束最多的动作（认为约束多的动作更有价值）
    let bestAction = legalActions[0];
    let maxConstraints = this.countConstraints(bestAction);
    
    for (let i = 1; i < legalActions.length; i++) {
      const action = legalActions[i];
      const constraintCount = this.countConstraints(action);
      if (constraintCount > maxConstraints) {
        bestAction = action;
        maxConstraints = constraintCount;
      }
    }
    
    return this.resolveActionConstraints(bestAction);
  }
  
  private countConstraints(action: RuleAction): number {
    if (!action.constraints) return 0;
    return Object.keys(action.constraints).length;
  }
  
  private resolveActionConstraints(template: RuleAction): RuleAction {
    const args = { ...(template.args ?? {}) };
    
    for (const [name, constraint] of Object.entries(template.constraints ?? {})) {
      if (args[name] !== undefined) continue;
      
      if (constraint.values?.length) {
        // 贪婪：选择第一个候选值（通常是最优的）
        args[name] = constraint.values[0];
      } else if (constraint.max !== undefined) {
        // 贪婪：选择最大值
        args[name] = constraint.max;
      } else if (constraint.min !== undefined) {
        args[name] = constraint.min;
      } else {
        throw new Error(`Cannot resolve constraint for ${template.type}.${name}`);
      }
    }
    
    return { ...template, args };
  }
}
