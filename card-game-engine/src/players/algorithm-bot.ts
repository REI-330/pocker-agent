import type { Player, DecisionContext, PlayerDecision } from "./types.js";
import type { BotStrategy } from "./strategies/bot-strategy.js";
import { DecisionError } from "./types.js";

/**
 * 算法Bot玩家 - 使用可插拔的策略模式
 * 支持运行时动态切换策略
 */
export class AlgorithmBot implements Player {
  readonly type = "algorithm-bot" as const;
  private strategy: BotStrategy;
  
  constructor(
    readonly id: string,
    initialStrategy: BotStrategy
  ) {
    this.strategy = initialStrategy;
  }
  
  async decideAction(context: DecisionContext): Promise<PlayerDecision> {
    const startTime = Date.now();
    
    try {
      const action = await this.strategy.selectAction(context);
      const thinkingTime = Date.now() - startTime;
      
      return {
        action,
        intent: {
          text: `${this.strategy.name}策略：选择 ${action.type}`,
          tags: ["algorithm-bot", this.strategy.name.toLowerCase()],
          confidence: 0.8
        },
        metadata: {
          thinkingTime,
          strategyUsed: this.strategy.name
        }
      };
    } catch (error) {
      throw new DecisionError(
        `Strategy ${this.strategy.name} failed: ${error instanceof Error ? error.message : String(error)}`,
        "STRATEGY_ERROR",
        this.id,
        error instanceof Error ? error : undefined
      );
    }
  }
  
  /**
   * 获取当前策略名称
   */
  getStrategyName(): string {
    return this.strategy.name;
  }
  
  /**
   * 动态切换策略
   * @param newStrategy 新策略
   */
  setStrategy(newStrategy: BotStrategy): void {
    this.strategy = newStrategy;
  }
  
  /**
   * 获取当前策略实例（用于高级配置）
   */
  getStrategy(): BotStrategy {
    return this.strategy;
  }
}
