import type {ConversationSnapshot, Rule, Runtime, ActionArguments, GameEvent} from './types'

export const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const DEFAULT_TIMEOUT = 120_000
export class ApiError extends Error { constructor(message: string, readonly status?: number) { super(message); this.name = 'ApiError' } }

export async function request<T>(path: string, body?: unknown, options: {signal?: AbortSignal; timeoutMs?: number} = {}): Promise<T> {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  options.signal?.addEventListener('abort', onAbort, {once: true})
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT)
  try {
    const response = await fetch(API + path, {method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? undefined : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal})
    const text = await response.text()
    let data: any = null
    if (text) { try { data = JSON.parse(text) } catch { throw new ApiError(`服务返回了无效响应（HTTP ${response.status}）`, response.status) } }
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : typeof data?.error === 'string' ? data.error : `请求失败（HTTP ${response.status}）`
      throw new ApiError(detail, response.status)
    }
    return data as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('请求已取消或超时')
    if (error instanceof TypeError) throw new ApiError('无法连接本机服务，请检查后端是否启动')
    throw error
  } finally { clearTimeout(timer); options.signal?.removeEventListener('abort', onAbort) }
}

export const conversationApi = {
  create: (signal?: AbortSignal) => request<ConversationSnapshot>('/api/conversations', {}, {signal}),
  get: (id: string, signal?: AbortSignal) => request<ConversationSnapshot>(`/api/conversations/${encodeURIComponent(id)}`, undefined, {signal}),
  send: (id: string, message: string, revision: number, request_id: string, signal?: AbortSignal) => request<ConversationSnapshot>(`/api/conversations/${encodeURIComponent(id)}/messages`, {message, revision, request_id}, {signal}),
  confirm: (id: string, revision: number, signal?: AbortSignal) => request<ConversationSnapshot>(`/api/conversations/${encodeURIComponent(id)}/confirm`, {revision}, {signal}),
  cancel: (id: string, revision: number) => request<ConversationSnapshot>(`/api/conversations/${encodeURIComponent(id)}/cancel`, {revision}),
}

export const gameApi = {
  runtime: (id: string, revision: number, seed?: number) => request<Runtime>(`/api/conversations/${encodeURIComponent(id)}/runtime`, {revision, ...(seed === undefined ? {} : {seed})}),
  simulation: (id: string, revision: number, seed?: number) => request<{completed: boolean; events: GameEvent[]}>(`/api/conversations/${encodeURIComponent(id)}/simulations`, {revision, ...(seed === undefined ? {} : {seed})}),
  action: (runtimeId: string, action: string, payload: ActionArguments & {revision: number; card_index: number}) => request<{state: Runtime}>(`/api/runtime/sessions/${encodeURIComponent(runtimeId)}/actions/${encodeURIComponent(action)}`, payload),
  getRuntime: (runtimeId: string) => request<Runtime>(`/api/runtime/sessions/${encodeURIComponent(runtimeId)}`),
}

export async function downloadGame(conversationId: string, revision: number, fallbackRules?: Rule) {
  const response = await fetch(API + `/api/conversations/${encodeURIComponent(conversationId)}/export`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({revision})})
  if (!response.ok) { let detail = '导出失败'; try { const data = await response.json(); detail = data.detail || detail } catch {} throw new ApiError(detail, response.status) }
  const url = URL.createObjectURL(await response.blob()); const link = document.createElement('a'); link.href = url; link.download = (fallbackRules?.game_id || conversationId) + '.pocker-game.zip'; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export const messageOf = (error: unknown) => error instanceof Error ? error.message : '操作失败，请重试'
