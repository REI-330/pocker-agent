import test from 'node:test'
import assert from 'node:assert/strict'
import {canConfirm, conversationReducer, isWorking, visibleMessages, type ConversationState} from '../src/features/conversation/state.ts'
import type {ConversationSnapshot} from '../src/shared/api/types.ts'

const snapshot = (overrides: Partial<ConversationSnapshot> = {}): ConversationSnapshot => ({id: 'c1', revision: 1, phase: 'designing', messages: [], draft: null, proposal: null, facts: [], tool_plan: null, job: null, error: null, runtime_id: null, ...overrides})
const initial: ConversationState = {snapshot: snapshot(), input: '下一条', error: '', notice: '', loading: false, operation: null, submission: null}

test('stale snapshots cannot overwrite a newer conversation revision', () => {
  const newer = conversationReducer(initial, {type: 'snapshot', snapshot: snapshot({revision: 4})})
  const stale = conversationReducer(newer, {type: 'snapshot', snapshot: snapshot({revision: 2, phase: 'failed'})})
  assert.equal(stale.snapshot?.revision, 4)
  assert.equal(stale.snapshot?.phase, 'designing')
})

test('submitted text is cleared without dropping text typed during the request', () => {
  const started = conversationReducer(initial, {type: 'begin', operation: 'send', submission: {id: 'r1', content: '第一条', messageCount: 0}})
  const typed = conversationReducer(started, {type: 'input', value: '第二条'})
  const failed = conversationReducer(typed, {type: 'failure', message: '暂时失败', restoreSubmission: true})
  assert.equal(started.input, '下一条')
  assert.equal(typed.input, '第二条')
  assert.equal(failed.input, '第二条')
})

test('pending user text appears once while waiting for the server snapshot', () => {
  const started = conversationReducer({...initial, input: '第一条'}, {type: 'begin', operation: 'send', submission: {id: 'r1', content: '第一条', messageCount: 0}})
  assert.deepEqual(visibleMessages(started).map(message => message.content), ['第一条'])
  const delivered = conversationReducer(started, {type: 'snapshot', snapshot: snapshot({phase: 'proposal_ready', messages: [{role: 'user', content: '第一条'}, {role: 'assistant', content: '摘要'}]})})
  assert.deepEqual(visibleMessages(delivered).map(message => message.content), ['第一条', '摘要'])
})

test('confirmation is available only for a draft in proposal_ready or failed', () => {
  assert.equal(canConfirm(snapshot({phase: 'designing', draft: {title: 'x', summary: 'y'}})), false)
  assert.equal(canConfirm(snapshot({phase: 'proposal_ready', draft: {title: 'x', summary: 'y'}})), true)
  assert.equal(canConfirm(snapshot({phase: 'failed', draft: {title: 'x', summary: 'y'}})), true)
  assert.equal(isWorking(snapshot({phase: 'thinking'})), true)
  assert.equal(isWorking(snapshot({phase: 'building'})), true)
})
