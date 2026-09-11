import type {ConversationSnapshot} from '../../shared/api/types'

export type Submission = {id: string; content: string; messageCount: number}
export type ConversationState = {
  snapshot: ConversationSnapshot | null; input: string; error: string; notice: string
  loading: boolean; operation: 'send' | 'confirm' | 'cancel' | null; submission: Submission | null
}
export type ConversationAction =
  | {type: 'input'; value: string}
  | {type: 'snapshot'; snapshot: ConversationSnapshot; replace?: boolean}
  | {type: 'begin'; operation: 'send' | 'confirm' | 'cancel'; submission?: Submission}
  | {type: 'end'}
  | {type: 'failure'; message: string; restoreSubmission?: boolean}
  | {type: 'loading'}
  | {type: 'notice'; message: string}

export function isWorking(snapshot: ConversationSnapshot | null) { return snapshot?.phase === 'thinking' || snapshot?.phase === 'building' }
export function canConfirm(snapshot: ConversationSnapshot | null) { return !!snapshot?.draft && ['proposal_ready', 'failed'].includes(snapshot.phase) }

export function conversationReducer(state: ConversationState, action: ConversationAction): ConversationState {
  switch (action.type) {
    case 'input': return {...state, input: action.value}
    case 'loading': return {...state, loading: true, error: ''}
    case 'notice': return {...state, notice: action.message}
    case 'snapshot': {
      if (!action.replace && state.snapshot && (action.snapshot.id !== state.snapshot.id || action.snapshot.revision < state.snapshot.revision)) return state
      return {...state, snapshot: action.snapshot, loading: false, error: '', ...(action.replace ? {submission: null, operation: null, input: ''} : {})}
    }
    case 'begin': return {...state, operation: action.operation, error: '', submission: action.submission ?? state.submission,
      input: action.submission && state.input.trim() === action.submission.content ? '' : state.input}
    case 'end': return {...state, operation: null, submission: null}
    case 'failure': return {...state, loading: false, error: action.message,
      input: action.restoreSubmission && !state.input && state.submission ? state.submission.content : state.input}
  }
}

export function visibleMessages(state: ConversationState) {
  const messages = state.snapshot?.messages || []
  const submitted = state.submission
  if (!submitted || messages.slice(submitted.messageCount).some(message => message.role === 'user' && message.content === submitted.content)) return messages
  return [...messages, {role: 'user' as const, content: submitted.content}]
}
