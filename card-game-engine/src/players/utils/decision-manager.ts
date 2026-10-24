import type { Player, DecisionContext, PlayerDecision } from "../types.js";
import { DecisionError } from "../types.js";

export interface DecisionManagerOptions {
  defaultTimeoutMs?: number;
  maxRetries?: number;
  enableFallback?: boolean;
}

export class DecisionManager {
  private readonly defaultTimeoutMs: number;
  private readonly maxRetries: number;
  private readonly enableFallback: boolean;

  constructor(options: DecisionManagerOptions = {}) {
    this.defaultTimeoutMs = options.defaultTimeoutMs ?? 30000;
    this.maxRetries = options.maxRetries ?? 1;
    this.enableFallback = options.enableFallback ?? true;
  }

  async executeDecision(player: Player, context: DecisionContext): Promise<PlayerDecision> {
    const timeoutMs = context.timeoutMs ?? this.defaultTimeoutMs;
    const ctx: DecisionContext = { ...context, timeoutMs };
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await this.withTimeout(player.decideAction(ctx), timeoutMs, player.id);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        if (
          error instanceof DecisionError &&
          (error.code === "TIMEOUT" || error.code === "CONNECTION_LOST") &&
          attempt < this.maxRetries
        ) {
          await this.delay(500 * (attempt + 1));
          continue;
        }
        throw error;
      }
    }

    if (this.enableFallback) {
      console.warn(`[DecisionManager] Player ${player.id} exhausted retries, using fallback`);
      return this.getFallbackDecision(context, lastError);
    }
    throw lastError!;
  }

  private withTimeout<T>(promise: Promise<T>, timeoutMs: number, playerId: string): Promise<T> {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new DecisionError(`Decision timeout after ${timeoutMs}ms`, "TIMEOUT", playerId)), timeoutMs)
      ),
    ]);
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private getFallbackDecision(context: DecisionContext, error?: Error): PlayerDecision {
    const { legalActions } = context;
    if (legalActions.length === 0) {
      throw new DecisionError("No legal actions available for fallback", "INVALID_ACTION", "fallback");
    }
    const template = legalActions[0];
    const args = { ...(template.args ?? {}) };
    for (const [name, constraint] of Object.entries(template.constraints ?? {})) {
      if (args[name] !== undefined) continue;
      if (constraint.values?.length) args[name] = constraint.values[0];
      else if (constraint.min !== undefined) args[name] = constraint.min;
    }
    return {
      action: { ...template, args },
      intent: { text: `降级策略：选择 ${template.type}`, tags: ["fallback"], confidence: 0.1 },
      metadata: { fallback: true, originalError: error?.message },
    };
  }
}
