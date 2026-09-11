import React, {useCallback, useEffect, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {API, gameApi, messageOf, type ModelConfig, type Runtime, type GameEvent, downloadGame} from './shared/api'
import {ModelSettings} from './features/settings/ModelSettings'
import {ConversationPanel} from './features/conversation/ConversationPanel'
import {RulesPanel} from './features/conversation/RulesPanel'
import {useConversation} from './features/conversation/useConversation'
import {GameTable} from './features/game/GameTable'
import './styles.css'; import './runtime.css'; import './config.css'

function App() {
  const conversation = useConversation()
  const {state, messages, runtimeId, setRuntimeId} = conversation
  const [runtime, setRuntime] = useState<Runtime | null>(null)
  const [events, setEvents] = useState<GameEvent[]>([])
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null)
  const [gameBusy, setGameBusy] = useState('')
  const [gameError, setGameError] = useState('')
  const [showConfig, setShowConfig] = useState(true)
  const snapshot = state.snapshot
  const status = gameBusy || state.operation === 'send' ? (gameBusy || 'Agent 回复中') : snapshot ? ({designing:'继续描述玩法', thinking:'Agent 思考中', proposal_ready:'规则摘要待确认', building:'正在生成游戏', playable:'游戏已就绪', failed:'操作失败，可重试'}[snapshot.phase]) : '正在连接会话…'
  const configured = !!modelConfig?.configured

  useEffect(() => { if (!runtimeId) return; gameApi.getRuntime(runtimeId).then(setRuntime).catch(error => setGameError(messageOf(error))) }, [runtimeId])
  const run = useCallback(async (label: string, task: () => Promise<void>) => { setGameBusy(label); setGameError(''); try { await task() } catch (error) { setGameError(messageOf(error)) } finally { setGameBusy('') } }, [])
  const start = () => { if (!snapshot?.proposal || snapshot.phase !== 'playable') return; void run('开始试玩', async () => { const data = await gameApi.runtime(snapshot.id, snapshot.revision); setRuntime(data); setRuntimeId(data.session_id) }) }
  const act = (action: string, index: number, args: any = {}) => { if (!runtime) return; void run('执行回合', async () => { const data = await gameApi.action(runtime.session_id, action, {...args, revision: runtime.revision, card_index: index}); setRuntime(data.state); setRuntimeId(data.state.session_id) }) }
  const refresh = () => { if (!runtimeId && !runtime) return; void run('刷新牌局', async () => setRuntime(await gameApi.getRuntime(runtime?.session_id || runtimeId!))) }
  const simulate = () => { if (!snapshot || snapshot.phase !== 'playable') return; void run('运行模拟', async () => { const data = await gameApi.simulation(snapshot.id, snapshot.revision, 7); if (!data.completed) throw new Error('模拟尚未完成'); setEvents(data.events) }) }
  const onNew = () => { setRuntime(null); setEvents([]); setGameError(''); void conversation.newConversation() }
  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">♠</span><div><strong>Pocker Agent</strong><small>把规则变成牌局</small></div></div><div className="top-actions"><span className="status" role="status">{status}</span><button className="config-link" onClick={() => setShowConfig(!showConfig)}>{showConfig ? '收起模型设置' : '模型设置'}</button></div></header>
    <div hidden={!showConfig}><ModelSettings onSaved={setModelConfig}/></div>
    {(state.error || gameError) && <div className="error" role="alert"><pre>{state.error || gameError}</pre></div>}
    {state.notice && <p className="support-note" role="status">{state.notice}</p>}
    <section className="hero"><p className="eyebrow">FROM IDEA TO PLAY</p><h1>写下规则。<br/>开始一局。</h1><p className="lede">和 Agent 一起补全玩法，确认规则，生成游戏，再与电脑试玩。</p></section>
    <section className="workspace">
      <ConversationPanel messages={messages} input={state.input} phase={snapshot?.phase || 'designing'} loading={state.loading} sending={state.operation === 'send'} canSend={configured && conversation.canSend} onInput={conversation.setInput} onSend={conversation.send} onCancel={conversation.cancel} onNew={onNew}/>
      <RulesPanel snapshot={snapshot} canConfirm={configured && conversation.canConfirm} confirming={state.operation === 'confirm'} onConfirm={conversation.confirm}/>
      <section className="panel trace"><div className="panel-head"><div><span className="kicker">03 / VERIFY</span><h2>模拟轨迹</h2></div><span className="pill">{events.length} 个事件</span></div>{events.length ? <div className="events">{events.map((event,i) => <div className="event" key={i}><span className="event-index">{i+1}</span><div><strong>{String(event.event)} · 第 {String(event.round)} 轮</strong><code>{JSON.stringify(event)}</code></div></div>)}</div> : <p className="empty tall">游戏生成完成后运行模拟，检查发牌、动作、计分和结果。</p>}{snapshot?.phase === 'playable' && <div className="rule-actions"><button className="secondary" disabled={!!gameBusy} onClick={simulate}>运行模拟</button></div>}</section>
      <GameTable state={runtime} busy={!!gameBusy} canStart={snapshot?.phase === 'playable'} start={start} act={act} refresh={refresh}/>
      <section className="export-bar"><div><span className="kicker">05 / TAKE IT WITH YOU</span><h2>把这局游戏带走</h2><p>{snapshot?.phase === 'playable' ? '导出服务端已验证的游戏包。' : '确认规则并完成生成后即可导出。'}</p></div><button className="primary" disabled={!snapshot || snapshot.phase !== 'playable' || !!gameBusy} onClick={() => void run('导出游戏', () => downloadGame(snapshot!.id, snapshot!.revision, snapshot!.proposal || undefined))}>下载游戏包</button></section>
    </section><footer>牌面素材：<a href="https://github.com/hayeah/playing-cards-assets" target="_blank" rel="noreferrer">Playing Cards Assets</a> · <a href={API + '/assets/cards/LICENSE'}>MIT License</a></footer>
  </main>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
