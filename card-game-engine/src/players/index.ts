// 核心类型
export type { Player, PlayerType, DecisionContext, PlayerDecision, GameObservation } from "./types.js";
export { DecisionError } from "./types.js";

// 玩家实现
export { AlgorithmBot } from "./algorithm-bot.js";
export { HumanPlayer } from "./human-player.js";
export { LLMAgent, createOpenAICompatibleClient } from "./llm-agent.js";
export type { LLMAgentOptions } from "./llm-agent.js";

// 策略
export type { BotStrategy } from "./strategies/bot-strategy.js";
export { RandomStrategy } from "./strategies/random-strategy.js";
export { GreedyStrategy } from "./strategies/greedy-strategy.js";
export { StrategyRegistry, defaultStrategyRegistry } from "./strategies/strategy-registry.js";

// 工具
export { DecisionManager } from "./utils/decision-manager.js";
export type { DecisionManagerOptions } from "./utils/decision-manager.js";
export { ObservationTransformer } from "./transformers/observation-transformer.js";

// 工厂
export { PlayerFactory } from "./player-factory.js";

// 适配器
export { ArenaPlayerAdapter } from "./adapters/arena-adapter.js";
