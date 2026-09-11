export type Message = {role: 'user' | 'assistant'; content: string}
export type ConversationPhase = 'designing' | 'thinking' | 'proposal_ready' | 'building' | 'playable' | 'failed'
export type Job = {id: string; status: 'running' | 'completed' | 'failed' | 'cancelled'; kind: 'chat' | 'build'; progress: {message: string; time: number}[]; error: string | null}
export type Rule = {
  kind?: 'arithmetic' | 'blackjack' | 'shedding' | 'doudizhu' | 'holdem' | 'plugin'; source?: string
  game_id: string; title: string; description: string; max_rounds: number
  players: {min_players: number; max_players: number; starting_hand_size: number}
  deck: {ranks: string[]; suits: string[]}; phases?: {name: string; actions: string[]; max_turns: number}[]
  actions?: {name: string; amount: number}[]
}
export type ConversationSnapshot = {
  id: string; revision: number; phase: ConversationPhase; messages: Message[]
  draft: {title: string; summary: string} | null; proposal: Rule | null; facts: string[]
  tool_plan: Record<string, unknown> | null; job: Job | null; error: string | null; runtime_id: string | null
}
export type ModelConfig = {configured: boolean; has_key: boolean; base_url: string; model: string; warning?: string}
export type Card = {rank: string; suit: string; value: number}
export type GameEvent = Record<string, unknown>
export type Runtime = {
  kind?: Rule['kind']; plugin_actions?: {id: string; label: string; target_player?: number; card_index?: number}[]
  numbers?: number[]; target?: number; instructions?: string; feedback?: string; result_title?: string
  legal_card_indices?: number[]; active_suit?: string; wild_rank?: string | null; suit_options?: string[]
  session_id: string; revision: number; seed?: number; round: number; max_rounds: number; phase: string
  current_player: string; finished: boolean; winners: string[]; finish_reason: string; legal_actions: string[]
  current_bet?: number; to_call?: number; players: {id: string; hand: Card[]; score: number; label?: string; hidden_count?: number; total?: number | null; chips?: number; committed?: number; hand_committed?: number; folded?: boolean}[]
  table: Card[]; board?: Card[]; pot?: number; side_pots?: {amount:number; eligible_players:number[]}[]; events: GameEvent[]; tool_events?: GameEvent[]; tool_plan?: Record<string, unknown>; deck_remaining: number
}
export type ActionArguments = {expression?: string; declared_suit?: string; amount?: number}
