import type { RuleAction } from "../../api.js";
import type { BotStrategy } from "./bot-strategy.js";
import type { DecisionContext } from "../types.js";

export class RandomStrategy implements BotStrategy {
  readonly name = "Random";
  
  selectAction(context: DecisionContext): RuleAction {
    const { legalActions } = context;
    if (legalActions.length === 0) {
      throw new Error("No legal actions available");
    }
    
    const index = Math.floor(Math.random() * legalActions.length);
    const template = legalActions[index];
    
    return this.resolveActionConstraints(template);
  }
  
  private resolveActionConstraints(template: RuleAction): RuleAction {
    const args = { ...(template.args ?? {}) };
    
    for (const [name, constraint] of Object.entries(template.constraints ?? {})) {
      if (args[name] !== undefined) continue;
      
      if (constraint.values?.length) {
        const idx = Math.floor(Math.random() * constraint.values.length);
        args[name] = constraint.values[idx];
      } else if (typeof constraint.min === "number" && typeof constraint.max === "number") {
        args[name] = Math.floor(Math.random() * (constraint.max - constraint.min + 1)) + constraint.min;
      } else if (typeof constraint.min === "number") {
        args[name] = constraint.min;
      } else {
        throw new Error(`Cannot resolve constraint for ${template.type}.${name}`);
      }
    }
    
    return { ...template, args };
  }
}
