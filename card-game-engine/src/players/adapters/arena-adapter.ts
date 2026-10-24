import type { Player, DecisionContext, PlayerDecision, GameObservation } from "../types.js";
import type { AgentDecisionInput, AgentDecision } from "../../arena.js";

export class ArenaPlayerAdapter {
  static toDecisionContext(input: AgentDecisionInput): DecisionContext {
    const observation: GameObservation = {
      gameId: input.gameId,
      instanceId: input.instanceId,
      playerId: input.playerId,
      sequence: input.sequence,
      state: input.observation,
      catalog: input.catalog,
    };
    return { observation, legalActions: input.legalActions };
  }

  static toAgentDecision(decision: PlayerDecision): AgentDecision {
    return { action: decision.action, intent: decision.intent };
  }

  static wrapPlayer(player: Player): {
    id: string;
    kind: "human" | "ai";
    decide(input: AgentDecisionInput): Promise<AgentDecision>;
  } {
    return {
      id: player.id,
      kind: player.type === "human" ? "human" : "ai",
      async decide(input: AgentDecisionInput): Promise<AgentDecision> {
        const context = ArenaPlayerAdapter.toDecisionContext(input);
        const decision = await player.decideAction(context);
        return ArenaPlayerAdapter.toAgentDecision(decision);
      },
    };
  }
}
