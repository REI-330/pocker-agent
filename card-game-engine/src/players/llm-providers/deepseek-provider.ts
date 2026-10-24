import type { LLMProvider, LLMProviderConfig, LLMCompletionRequest, LLMCompletionResponse } from "./types.js";

export class DeepSeekProvider implements LLMProvider {
  readonly name = "DeepSeek";
  
  constructor(private config: LLMProviderConfig) {}
  
  async complete(request: LLMCompletionRequest): Promise<LLMCompletionResponse> {
    const response = await fetch(this.config.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        model: request.model || this.config.model || "deepseek-chat",
        messages: request.messages,
        temperature: request.temperature ?? 0.7,
        max_tokens: request.maxTokens,
      }),
      signal: AbortSignal.timeout(this.config.timeout || 30000),
    });
    
    if (!response.ok) {
      throw new Error(`DeepSeek API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return {
      content: data.choices[0]?.message?.content || "",
      finishReason: data.choices[0]?.finish_reason,
      usage: data.usage ? {
        promptTokens: data.usage.prompt_tokens,
        completionTokens: data.usage.completion_tokens,
        totalTokens: data.usage.total_tokens,
      } : undefined,
    };
  }
}
