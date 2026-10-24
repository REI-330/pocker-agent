export * from "./types.js";
export { DeepSeekProvider } from "./deepseek-provider.js";
export { OpenAIProvider } from "./openai-provider.js";
export { ClaudeProvider } from "./claude-provider.js";

import type { LLMProvider, LLMProviderConfig } from "./types.js";
import { DeepSeekProvider } from "./deepseek-provider.js";
import { OpenAIProvider } from "./openai-provider.js";
import { ClaudeProvider } from "./claude-provider.js";

export type LLMProviderType = "deepseek" | "openai" | "claude" | "custom";

export function createLLMProvider(
  type: LLMProviderType,
  config: LLMProviderConfig
): LLMProvider {
  switch (type) {
    case "deepseek":
      return new DeepSeekProvider(config);
    case "openai":
      return new OpenAIProvider(config);
    case "claude":
      return new ClaudeProvider(config);
    case "custom":
      return new OpenAIProvider(config);
    default:
      throw new Error(`Unknown LLM provider type: ${type}`);
  }
}
