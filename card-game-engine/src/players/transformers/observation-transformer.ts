import type { GameObservation } from "../types.js";

/**
 * 观察转换器 - 为不同玩家类型转换游戏状态格式
 */
export class ObservationTransformer {
  /**
   * 为人类玩家转换 - 保留完整JSON结构
   */
  static toHumanFormat(observation: GameObservation): Record<string, unknown> {
    return observation.state;
  }

  /**
   * 为算法Bot转换 - 提取关键特征
   */
  static toBotFeatures(observation: GameObservation): {
    handSize: number;
    deckSize: number;
    playerCount: number;
    turnPhase: string;
    [key: string]: unknown;
  } {
    const state = observation.state;
    
    // 提取常见特征
    const features: any = {
      handSize: 0,
      deckSize: 0,
      playerCount: 0,
      turnPhase: "unknown",
    };

    // 提取手牌数量
    if (state.hands && typeof state.hands === "object") {
      const hands = state.hands as Record<string, unknown>;
      if (hands[observation.playerId]) {
        const hand = hands[observation.playerId];
        if (Array.isArray(hand)) {
          features.handSize = hand.length;
        }
      }
    }

    // 提取牌堆大小
    if (state.deck && typeof state.deck === "object") {
      const deck = state.deck as any;
      if (Array.isArray(deck.cards)) {
        features.deckSize = deck.cards.length;
      } else if (typeof deck.count === "number") {
        features.deckSize = deck.count;
      }
    }

    // 提取玩家数量
    if (state.players && Array.isArray(state.players)) {
      features.playerCount = state.players.length;
    }

    // 提取回合阶段
    if (typeof state.phase === "string") {
      features.turnPhase = state.phase;
    } else if (typeof state.stage === "string") {
      features.turnPhase = state.stage;
    }

    return features;
  }

  /**
   * 为LLM转换 - 构建自然语言描述
   */
  static toLLMDescription(observation: GameObservation): string {
    const state = observation.state;
    const parts: string[] = [];

    parts.push(`玩家 ${observation.playerId} 的视角：`);

    // 描述手牌
    if (state.hands && typeof state.hands === "object") {
      const hands = state.hands as Record<string, unknown>;
      if (hands[observation.playerId]) {
        const hand = hands[observation.playerId];
        if (Array.isArray(hand)) {
          parts.push(`手牌数量：${hand.length}`);
          if (hand.length > 0 && hand.length <= 20) {
            const cardStr = hand
              .map((card: any) => {
                if (typeof card === "object" && card.suit && card.rank) {
                  return `${card.suit}${card.rank}`;
                }
                return JSON.stringify(card);
              })
              .join(", ");
            parts.push(`手牌：${cardStr}`);
          }
        }
      }
    }

    // 描述牌堆
    if (state.deck && typeof state.deck === "object") {
      const deck = state.deck as any;
      if (typeof deck.count === "number") {
        parts.push(`牌堆剩余：${deck.count}张`);
      } else if (Array.isArray(deck.cards)) {
        parts.push(`牌堆剩余：${deck.cards.length}张`);
      }
    }

    // 描述回合状态
    if (typeof state.currentPlayer === "string") {
      parts.push(`当前玩家：${state.currentPlayer}`);
    }
    if (typeof state.phase === "string") {
      parts.push(`阶段：${state.phase}`);
    }

    // 描述其他玩家
    if (state.players && Array.isArray(state.players)) {
      const others = state.players.filter((p: any) => p !== observation.playerId);
      if (others.length > 0) {
        parts.push(`其他玩家：${others.join(", ")}`);
      }
    }

    return parts.join("\n");
  }
}
