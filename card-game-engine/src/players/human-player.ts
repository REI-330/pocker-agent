import type { Player, DecisionContext, PlayerDecision } from "./types.js";
import { DecisionError } from "./types.js";
import type { RuleAction } from "../api.js";

/**
 * WebSocket消息类型
 */
interface RequestActionMessage {
  type: "request_action";
  playerId: string;
  observation: Record<string, unknown>;
  legalActions: readonly RuleAction[];
  timeoutMs?: number;
}

interface ActionResponseMessage {
  type: "action_response";
  playerId: string;
  action: RuleAction;
  intent?: {
    text?: string;
    confidence?: number;
  };
}

/**
 * 人类玩家 - 通过WebSocket与前端通信
 */
export class HumanPlayer implements Player {
  readonly type = "human" as const;
  
  private pendingDecision?: {
    resolve: (decision: PlayerDecision) => void;
    reject: (error: Error) => void;
    timeoutHandle?: NodeJS.Timeout;
  };
  
  constructor(
    readonly id: string,
    private readonly sendMessage: (message: RequestActionMessage) => void
  ) {}
  
  async decideAction(context: DecisionContext): Promise<PlayerDecision> {
    if (this.pendingDecision) {
      throw new DecisionError(
        "Human player is already waiting for a decision",
        "INVALID_ACTION",
        this.id
      );
    }
    
    const timeoutMs = context.timeoutMs ?? 60000; // 默认60秒超时
    
    return new Promise((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        this.pendingDecision = undefined;
        reject(new DecisionError(
          `Human player ${this.id} decision timeout after ${timeoutMs}ms`,
          "TIMEOUT",
          this.id
        ));
      }, timeoutMs);
      
      this.pendingDecision = { resolve, reject, timeoutHandle };
      
      // 发送请求给前端
      this.sendMessage({
        type: "request_action",
        playerId: this.id,
        observation: context.observation.state,
        legalActions: context.legalActions,
        timeoutMs
      });
    });
  }
  
  /**
   * 提交人类玩家的动作（由WebSocket消息处理器调用）
   */
  submitAction(response: ActionResponseMessage): void {
    if (!this.pendingDecision) {
      throw new DecisionError(
        `Human player ${this.id} is not waiting for a decision`,
        "INVALID_ACTION",
        this.id
      );
    }
    
    if (response.playerId !== this.id) {
      throw new DecisionError(
        `Action response playerId ${response.playerId} does not match ${this.id}`,
        "INVALID_ACTION",
        this.id
      );
    }
    
    const { resolve, timeoutHandle } = this.pendingDecision;
    this.pendingDecision = undefined;
    
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
    }
    
    resolve({
      action: response.action,
      intent: response.intent ? {
        text: response.intent.text || `玩家选择 ${response.action.type}`,
        tags: ["human"],
        confidence: response.intent.confidence
      } : undefined
    });
  }
  
  /**
   * 取消当前等待的决策
   */
  cancelDecision(reason?: string): void {
    if (this.pendingDecision) {
      const { reject, timeoutHandle } = this.pendingDecision;
      this.pendingDecision = undefined;
      
      if (timeoutHandle) {
        clearTimeout(timeoutHandle);
      }
      
      reject(new DecisionError(
        reason || "Decision cancelled",
        "CONNECTION_LOST",
        this.id
      ));
    }
  }
  
  dispose(): void {
    this.cancelDecision("Player disposed");
  }
}
