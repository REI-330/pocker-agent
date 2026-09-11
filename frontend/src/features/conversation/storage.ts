export const STORAGE_KEY = 'pocker-conversation-v3'
export type SavedWorkspace = {id: string | null; input: string; runtime_id: string | null}
export function restoreWorkspace(): SavedWorkspace & {notice: string} {
  const empty = {id: null, input: '', runtime_id: null, notice: ''}
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (!value) return {...empty, notice: localStorage.getItem('pocker-workbench-v2') ? '检测到旧版浏览器草稿。旧版状态未合并，请在新会话中重新描述玩法。' : ''}
    const parsed = JSON.parse(value)
    if ((parsed.id !== null && typeof parsed.id !== 'string') || typeof parsed.input !== 'string' || (parsed.runtime_id !== null && typeof parsed.runtime_id !== 'string')) throw new Error('invalid local workspace')
    return {...parsed, notice: ''}
  } catch { return {...empty, notice: '本机草稿无法读取，已打开空白会话。'} }
}
export function saveWorkspace(workspace: SavedWorkspace) { localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace)) }
