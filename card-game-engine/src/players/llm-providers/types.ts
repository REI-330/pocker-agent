/**
 * LLM提供者统一接口
 * 支持DeepSeek、OpenAI、Claude等多种LLM
 */

export interface LLMMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface LLMCompletionRequest {
  messages: LLMMessage[];
  temperature?: number;
  maxTokens?: number;
  model?: string;
}

export interface LLMCompletionResponse {
  content: string;
  finishReason?: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface LLMProvider {
  readonly name: string;
  complete(request: LLMCompletionRequest): Promise<LLMCompletionResponse>;
}

export interface LLMProviderConfig {
  apiUrl: string;
  apiKey: string;
  model?: string;
  timeout?: number;
}
