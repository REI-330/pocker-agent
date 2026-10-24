import type { Player, DecisionContext, PlayerDecision } from "./types.js";
import { DecisionError } from "./types.js";
import type { RuleAction } from "../api.js";

/**
 * LLM API 消息格式（兼容 OpenAI）
 */
interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface LLMClientOptions {
  apiUrl: string;
  apiKey: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
}

interface LLMClient {
  complete(messages: ChatMessage[]): Promise<string>;
}

/**
 * LLM Agent 配置
 */
export interface LLMAgentOptions {
  client: LLMClient;
  systemPrompt?: string;
  maxRetries?: number;
  fallbackStrategy?: "random" | "first";
  /** 保留的历史轮数（0表示无历史）*/
  historyRounds?: number;
}

/**
 * 构建提示词
 */
function buildPrompt(context: DecisionContext): string {
  const { observation, legalActions } = context;
  const { state } = observation;

  const stateStr = JSON.stringify(state, null, 2);
  const actionsStr = legalActions.map((a, i) =>
    `${i + 1}. ${a.type}${Object.keys(a.args ?? {}).length ? " " + JSON.stringify(a.args) : ""}${
      Object.keys(a.constraints ?? {}).length
        ? " (可选参数: " + Object.entries(a.constraints!).map(([k, c]) =>
            `${k}=${c.values ? c.values.join("/") : `${c.min ?? ""}~${c.max ?? ""}`}`
          ).join(", ") + ")"
        : ""
    }`
  ).join("\n");

  return `当前游戏状态：
\`\`\`json
${stateStr}
\`\`\`

你的玩家ID：${observation.playerId}
当前回合序号：${observation.sequence}

合法动作列表：
${actionsStr}

请从上述合法动作中选择一个动作。
仅输出以下格式的JSON，不要输出任何其他内容：
{"actionIndex": <1到${legalActions.length}的整数>, "reason": "<简短的选择理由>"}`;
}

/**
 * 解析 LLM 返回的动作
 */
function parseActionFromResponse(
  response: string,
  legalActions: readonly RuleAction[]
): { action: RuleAction; reason: string } | null {
  // 尝试直接解析 JSON
  const jsonMatch = response.match(/\{[\s\S]*\}/);
  if (!jsonMatch) return null;

  try {
    const parsed = JSON.parse(jsonMatch[0]) as { actionIndex?: unknown; reason?: unknown };
    const index = Number(parsed.actionIndex);
    if (!Number.isInteger(index) || index < 1 || index > legalActions.length) return null;

    const template = legalActions[index - 1];
    const action = resolveConstraints(template);
    return { action, reason: String(parsed.reason ?? "") };
  } catch {
    return null;
  }
}

function resolveConstraints(template: RuleAction): RuleAction {
  const args = { ...(template.args ?? {}) };
  for (const [name, constraint] of Object.entries(template.constraints ?? {})) {
    if (args[name] !== undefined) continue;
    if (constraint.values?.length) {
      args[name] = constraint.values[0];
    } else if (constraint.min !== undefined) {
      args[name] = constraint.min;
    } else {
      throw new Error(`Cannot resolve constraint for ${template.type}.${name}`);
    }
  }
  return { ...template, args };
}

/**
 * LLM 大模型 Agent 玩家
 */
export class LLMAgent implements Player {
  readonly type = "llm-agent" as const;

  private readonly maxRetries: number;
  private readonly fallbackStrategy: "random" | "first";
  private readonly historyRounds: number;
  private readonly systemPrompt: string;
  private conversationHistory: ChatMessage[] = [];

  constructor(
    readonly id: string,
    private readonly llmClient: LLMClient,
    options: Omit<LLMAgentOptions, "client"> = {}
  ) {
    this.maxRetries = options.maxRetries ?? 2;
    this.fallbackStrategy = options.fallbackStrategy ?? "first";
    this.historyRounds = options.historyRounds ?? 4;
    this.systemPrompt =
      options.systemPrompt ??
      "你是一个卡牌游戏AI。根据当前游戏状态和合法动作，选择最优的一步。只输出规定格式的JSON，不要有任何其他文字。";
  }

  async decideAction(context: DecisionContext): Promise<PlayerDecision> {
    const startTime = Date.now();
    const userPrompt = buildPrompt(context);

    const messages: ChatMessage[] = [
      { role: "system", content: this.systemPrompt },
      ...this.getTrimmedHistory(),
      { role: "user", content: userPrompt },
    ];

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await this.llmClient.complete(messages);
        const parsed = parseActionFromResponse(response, context.legalActions);

        if (parsed) {
          // 将本轮对话加入历史
          this.addToHistory({ role: "user", content: userPrompt });
          this.addToHistory({ role: "assistant", content: response });

          return {
            action: parsed.action,
            intent: {
              text: parsed.reason || `LLM选择 ${parsed.action.type}`,
              tags: ["llm-agent"],
              confidence: 0.9,
            },
            metadata: {
              thinkingTime: Date.now() - startTime,
              strategyUsed: "LLM",
              attempt: attempt + 1,
            },
          };
        }

        // 解析失败，添加重试提示
        messages.push({ role: "assistant", content: response });
        messages.push({
          role: "user",
          content: `输出格式有误，请严格按照 {"actionIndex": <数字>, "reason": "<理由>"} 格式重新输出，动作序号需在 1 到 ${context.legalActions.length} 之间。`,
        });
        lastError = new Error(`LLM parse failed on attempt ${attempt + 1}: ${response.slice(0, 200)}`);
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        if (attempt < this.maxRetries) {
          await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
        }
      }
    }

    // 所有重试耗尽，使用降级策略
    console.warn(`[LLMAgent:${this.id}] Falling back to ${this.fallbackStrategy} after ${this.maxRetries + 1} attempts`);
    const fallbackAction = this.getFallbackAction(context);
    return {
      action: fallbackAction,
      intent: {
        text: `降级到${this.fallbackStrategy}策略：选择 ${fallbackAction.type}`,
        tags: ["llm-agent", "fallback"],
        confidence: 0.3,
      },
      metadata: {
        thinkingTime: Date.now() - startTime,
        strategyUsed: `fallback-${this.fallbackStrategy}`,
        fallback: true,
        error: lastError?.message,
      },
    };
  }

  private getFallbackAction(context: DecisionContext): RuleAction {
    const { legalActions } = context;
    if (this.fallbackStrategy === "random") {
      const template = legalActions[Math.floor(Math.random() * legalActions.length)];
      return resolveConstraints(template);
    }
    return resolveConstraints(legalActions[0]);
  }

  private getTrimmedHistory(): ChatMessage[] {
    if (this.historyRounds <= 0) return [];
    const keep = this.historyRounds * 2; // user + assistant per round
    return this.conversationHistory.slice(-keep);
  }

  private addToHistory(message: ChatMessage): void {
    this.conversationHistory.push(message);
    // 防止无限增长
    if (this.conversationHistory.length > this.historyRounds * 2 + 20) {
      this.conversationHistory = this.conversationHistory.slice(-(this.historyRounds * 2));
    }
  }

  clearHistory(): void {
    this.conversationHistory = [];
  }

  dispose(): void {
    this.clearHistory();
  }
}

/**
 * 使用 OpenAI 兼容接口创建 LLMClient
 */
export function createOpenAICompatibleClient(options: LLMClientOptions): LLMClient {
  return {
    async complete(messages: ChatMessage[]): Promise<string> {
      const response = await fetch(options.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${options.apiKey}`,
        },
        body: JSON.stringify({
          model: options.model,
          messages,
          max_tokens: options.maxTokens ?? 512,
          temperature: options.temperature ?? 0.2,
        }),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`LLM API error ${response.status}: ${text.slice(0, 200)}`);
      }

      const data = (await response.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
      };
      const content = data.choices?.[0]?.message?.content;
      if (!content) throw new Error("LLM API returned empty content");
      return content;
    },
  };
}
