import type { RuleAction } from "../api.js";

/** 玩家类型 */
export type PlayerType = "human" | "algorithm-bot" | "llm-agent";

/** 游戏观察数据 */
export interface GameObservation {
  gameId: string;
  instanceId: string;
  playerId: string;
  sequence: number;
  state: Record<string, unknown>;
  catalog: unknown;
}

/** 决策上下文 */
export interface DecisionContext {
  observation: GameObservation;
  legalActions: readonly RuleAction[];
  timeoutMs?: number;
}

/** 决策结果 */
export interface PlayerDecision {
  action: RuleAction;
  intent?: {
    text: string;
    tags?: string[];
    confidence?: number;
  };
  metadata?: {
    thinkingTime?: number;
    strategyUsed?: string;
    [key: string]: unknown;
  };
}

/** 统一的玩家接口 */
export interface Player {
  readonly id: string;
  readonly type: PlayerType;
  
  /**
   * 根据观察和合法动作做出决策
   * @param context 决策上下文
   * @returns 玩家的决策
   */
  decideAction(context: DecisionContext): Promise<PlayerDecision>;
  
  /**
   * 清理资源（可选）
   */
  dispose?(): void | Promise<void>;
}

/** 决策错误类型 */
export class DecisionError extends Error {
  constructor(
    message: string,
    public readonly code: "TIMEOUT" | "INVALID_ACTION" | "CONNECTION_LOST" | "STRATEGY_ERROR" | "LLM_ERROR",
    public readonly playerId: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = "DecisionError";
  }
}
