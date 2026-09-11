import {useCallback, useEffect, useReducer, useRef, useState} from 'react'
import {messageOf} from '../../shared/api/client'
import type {ConversationSnapshot} from '../../shared/api/types'
import {conversationApi} from './api'
import {canConfirm, conversationReducer, isWorking, visibleMessages} from './state'
import {restoreWorkspace, saveWorkspace} from './storage'

export function useConversation() {
  const [saved] = useState(restoreWorkspace)
  const [state, dispatch] = useReducer(conversationReducer, {snapshot: null, input: saved.input, error: '', notice: saved.notice, loading: true, operation: null, submission: null})
  const current = useRef(state); current.current = state
  const controller = useRef<AbortController | null>(null)
  const bootstrap = useRef<Promise<ConversationSnapshot> | null>(null)
  const operationLock = useRef(false)
  const epoch = useRef(0)
  const [runtimeId, setRuntimeId] = useState(saved.runtime_id)

  useEffect(() => {
    let active = true
    if (!bootstrap.current) bootstrap.current = saved.id ? conversationApi.get(saved.id) : conversationApi.create()
    bootstrap.current.then(snapshot => { if (active) dispatch({type: 'snapshot', snapshot}) })
      .catch(error => { if (active) dispatch({type: 'failure', message: messageOf(error)}) })
    return () => { active = false }
  }, [saved.id])

  useEffect(() => {
    try { saveWorkspace({id: state.snapshot?.id ?? saved.id, input: state.input, runtime_id: runtimeId}) }
    catch { dispatch({type: 'notice', message: '浏览器无法保存草稿；刷新页面可能丢失尚未发送的文字。'}) }
  }, [state.snapshot?.id, state.input, runtimeId, saved.id])

  const sync = useCallback(async () => {
    const snapshot = current.current.snapshot
    const id = snapshot?.id || saved.id
    if (!id) return
    const updated = await conversationApi.get(id)
    dispatch({type: 'snapshot', snapshot: updated})
    return updated
  }, [saved.id])

  useEffect(() => {
    if (!state.snapshot || (!isWorking(state.snapshot) && state.operation !== 'send')) return
    const id = state.snapshot.id
    let active = true; let timer: ReturnType<typeof setTimeout>; let failures = 0
    async function poll() {
      try { const snapshot = await conversationApi.get(id); if (!active) return; failures = 0; dispatch({type: 'snapshot', snapshot}) }
      catch (error) { if (!active) return; failures++; if (failures >= 3) dispatch({type: 'failure', message: `连接暂时中断，正在重试同步。${messageOf(error)}`}) }
      if (active) timer = setTimeout(() => void poll(), failures ? 3000 : 1000)
    }
    timer = setTimeout(() => void poll(), 500)
    return () => { active = false; clearTimeout(timer) }
  }, [state.snapshot?.id, state.snapshot?.phase, state.operation])

  async function perform(operation: 'send' | 'confirm') {
    const before = current.current
    if (!before.snapshot || operationLock.current || isWorking(before.snapshot)) return
    const content = before.input.trim()
    if ((operation === 'send' && !content) || (operation === 'confirm' && !canConfirm(before.snapshot))) return
    const submission = operation === 'send' ? {id: crypto.randomUUID(), content, messageCount: before.snapshot.messages.length} : undefined
    operationLock.current = true; const ownEpoch = epoch.current; const ownController = new AbortController(); controller.current = ownController
    dispatch({type: 'begin', operation, submission})
    try {
      const snapshot = operation === 'send'
        ? await conversationApi.send(before.snapshot.id, content, before.snapshot.revision, submission!.id, ownController.signal)
        : await conversationApi.confirm(before.snapshot.id, before.snapshot.revision, ownController.signal)
      if (epoch.current === ownEpoch) { dispatch({type: 'snapshot', snapshot}); if (operation === 'send') setRuntimeId(null) }
    } catch (error) {
      if (epoch.current !== ownEpoch) return
      try {
        const recovered = await sync()
        if (!recovered || (!isWorking(recovered) && recovered.messages.length <= before.snapshot.messages.length)) dispatch({type: 'failure', message: messageOf(error), restoreSubmission: true})
      } catch { dispatch({type: 'failure', message: `${messageOf(error)}。可刷新会话检查结果。`, restoreSubmission: true}) }
    } finally {
      if (epoch.current === ownEpoch) { operationLock.current = false; controller.current = null; dispatch({type: 'end'}) }
    }
  }

  async function cancel() {
    const snapshot = current.current.snapshot
    if (!snapshot || current.current.operation === 'cancel') return
    epoch.current++; controller.current?.abort(); controller.current = null; operationLock.current = true
    dispatch({type: 'begin', operation: 'cancel'})
    try {
      const latest = await conversationApi.get(snapshot.id)
      dispatch({type: 'snapshot', snapshot: isWorking(latest) ? await conversationApi.cancel(latest.id, latest.revision) : latest})
    } catch (error) { dispatch({type: 'failure', message: messageOf(error), restoreSubmission: true}) }
    finally { operationLock.current = false; dispatch({type: 'end'}) }
  }

  async function newConversation() {
    if (operationLock.current || isWorking(current.current.snapshot)) return
    operationLock.current = true; epoch.current++; dispatch({type: 'loading'})
    try { const snapshot = await conversationApi.create(); setRuntimeId(null); dispatch({type: 'snapshot', snapshot, replace: true}) }
    catch (error) { dispatch({type: 'failure', message: messageOf(error)}) }
    finally { operationLock.current = false }
  }

  return {state, messages: visibleMessages(state), runtimeId, setRuntimeId, setInput: (value: string) => dispatch({type: 'input', value}), send: () => perform('send'), confirm: () => perform('confirm'), cancel, newConversation,
    refresh: () => sync().catch(error => dispatch({type: 'failure', message: messageOf(error)})), working: isWorking(state.snapshot) || state.operation === 'send', canConfirm: canConfirm(state.snapshot) && !state.operation, canSend: !!state.snapshot && !isWorking(state.snapshot) && !state.operation && !state.loading}
}
