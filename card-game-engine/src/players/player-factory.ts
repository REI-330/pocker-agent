import type { Player } from "./types.js";
import { AlgorithmBot } from "./algorithm-bot.js";
import { HumanPlayer } from "./human-player.js";
import { LLMAgent, createOpenAICompatibleClient } from "./llm-agent.js";
import type { BotStrategy } from "./strategies/bot-strategy.js";
import { defaultStrategyRegistry } from "./strategies/strategy-registry.js";

/**
 * 玩家工厂 - 简化玩家实例创建
 */
export class PlayerFactory {
  /**
   * 创建算法Bot
   */
  static createAlgorithmBot(id: string, strategyName: string): AlgorithmBot {
    const strategy = defaultStrategyRegistry.get(strategyName);
    if (!strategy) {
      throw new Error(`Strategy ${strategyName} not found in registry`);
    }
    return new AlgorithmBot(id, strategy);
  }

  /**
   * 使用自定义策略创建算法Bot
   */
  static createAlgorithmBotWithStrategy(id: string, strategy: BotStrategy): AlgorithmBot {
    return new AlgorithmBot(id, strategy);
  }

  /**
   * 创建人类玩家
   */
  static createHumanPlayer(
    id: string,
    sendMessage: (message: any) => void
  ): HumanPlayer {
    return new HumanPlayer(id, sendMessage);
  }

  /**
   * 创建LLM Agent（OpenAI兼容）
   */
  static createLLMAgent(
    id: string,
    options: {
      apiUrl: string;
      apiKey: string;
      model: string;
      systemPrompt?: string;
      maxTokens?: number;
      temperature?: number;
      maxRetries?: number;
      fallbackStrategy?: "random" | "first";
      historyRounds?: number;
    }
  ): LLMAgent {
    const client = createOpenAICompatibleClient({
      apiUrl: options.apiUrl,
      apiKey: options.apiKey,
      model: options.model,
      maxTokens: options.maxTokens,
      temperature: options.temperature,
    });

    return new LLMAgent(id, client, {
      systemPrompt: options.systemPrompt,
      maxRetries: options.maxRetries,
      fallbackStrategy: options.fallbackStrategy,
      historyRounds: options.historyRounds,
    });
  }
}
