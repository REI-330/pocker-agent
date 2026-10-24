import type { LLMProvider, LLMProviderConfig, LLMCompletionRequest, LLMCompletionResponse } from "./types.js";

export class ClaudeProvider implements LLMProvider {
  readonly name = "Claude";
  
  constructor(private config: LLMProviderConfig) {}
  
  async complete(request: LLMCompletionRequest): Promise<LLMCompletionResponse> {
    const response = await fetch(this.config.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": this.config.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: request.model || this.config.model || "claude-3-5-sonnet-20241022",
        messages: request.messages.filter(m => m.role !== "system"),
        system: request.messages.find(m => m.role === "system")?.content,
        temperature: request.temperature ?? 0.7,
        max_tokens: request.maxTokens || 1024,
      }),
      signal: AbortSignal.timeout(this.config.timeout || 30000),
    });
    
    if (!response.ok) {
      throw new Error(`Claude API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return {
      content: data.content[0]?.text || "",
      finishReason: data.stop_reason,
      usage: data.usage ? {
        promptTokens: data.usage.input_tokens,
        completionTokens: data.usage.output_tokens,
        totalTokens: data.usage.input_tokens + data.usage.output_tokens,
      } : undefined,
    };
  }
}
