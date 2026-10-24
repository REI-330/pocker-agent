import type { BotStrategy } from "./bot-strategy.js";
import { RandomStrategy } from "./random-strategy.js";
import { GreedyStrategy } from "./greedy-strategy.js";

/**
 * 策略注册表 - 运行时管理可用策略
 */
export class StrategyRegistry {
  private strategies = new Map<string, BotStrategy>();
  
  constructor() {
    // 注册默认策略
    this.register(new RandomStrategy());
    this.register(new GreedyStrategy());
  }
  
  /**
   * 注册新策略
   */
  register(strategy: BotStrategy): void {
    const key = strategy.name.toLowerCase();
    if (this.strategies.has(key)) {
      console.warn(`Strategy ${strategy.name} is already registered, overwriting`);
    }
    this.strategies.set(key, strategy);
  }
  
  /**
   * 获取策略
   */
  get(name: string): BotStrategy | undefined {
    return this.strategies.get(name.toLowerCase());
  }
  
  /**
   * 列出所有策略名称
   */
  list(): string[] {
    return Array.from(this.strategies.keys());
  }
  
  /**
   * 检查策略是否存在
   */
  has(name: string): boolean {
    return this.strategies.has(name.toLowerCase());
  }
}

/**
 * 全局默认策略注册表
 */
export const defaultStrategyRegistry = new StrategyRegistry();
