import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Check, ChevronRight, CircleAlert, Play, Send, Sparkles } from 'lucide-react'
import './styles.css'
import './runtime.css'
import './config.css'

type Turn = { role: 'user' | 'assistant'; content: string }
type Rule = Record<string, unknown>

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function App() {
  const [input, setInput] = useState('我想做一个两人比大小游戏，每人一张牌，翻开后点数高的人获胜。')
  const [turns, setTurns] = useState<Turn[]>([])
  const [proposal, setProposal] = useState<Rule | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [status, setStatus] = useState('等待描述玩法')
  const [events, setEvents] = useState<Record<string, unknown>[]>([])
  const [runtime, setRuntime] = useState<{session_id: string; current_player: string; legal_actions: string[]; players: {id: string; hand: {rank: string; suit: string}[]}[]; table: {rank: string; suit: string}[]; finished: boolean} | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showConfig, setShowConfig] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1')
  const [model, setModel] = useState('gpt-4o-mini')

  async function askAgent() {
    if (!input.trim() || busy) return
    setBusy(true); setError('')
    const next = [...turns, { role: 'user' as const, content: input.trim() }]
    try {
      const response = await fetch(`${API}/api/agent/turn`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ message: input.trim(), messages: turns.map(turn => ({ role: turn.role, content: turn.content })), proposal }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Agent 请求失败')
      setTurns([...next, { role: 'assistant', content: data.message }])
      if (data.rules) setProposal(data.rules)
      if (data.rules) setConfirmed(false)
      setStatus(data.kind === 'proposal' ? '规则待确认' : data.kind === 'question' ? '等待补充信息' : '需要修正规则')
      if (data.errors?.length) setError(data.errors.join('\n'))
      setInput('')
    } catch (err) { setError(err instanceof Error ? err.message : '请求失败') }
    finally { setBusy(false) }
  }

  async function configureModel() {
    if (!apiKey.trim() || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/agent/config`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '配置失败')
      setApiKey(''); setShowConfig(false); setStatus(`模型已配置 · ${data.model}`)
    } catch (err) { setError(err instanceof Error ? err.message : '配置失败') }
    finally { setBusy(false) }
  }

  async function simulate() {
    if (!proposal || !confirmed || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/simulations?seed=7`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(proposal) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '模拟失败')
      setEvents(data.events || []); setStatus(`模拟完成 · ${data.winner || '无胜者'}`)
    } catch (err) { setError(err instanceof Error ? err.message : '模拟失败') }
    finally { setBusy(false) }
  }

  async function startRuntime() {
    if (!proposal || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/runtime/sessions?seed=7`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(proposal) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '试玩启动失败')
      setRuntime(data); setStatus('试玩中 · 轮到 ' + data.current_player)
    } catch (err) { setError(err instanceof Error ? err.message : '试玩启动失败') }
    finally { setBusy(false) }
  }

  async function playAction(action: string) {
    if (!runtime || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/runtime/sessions/${runtime.session_id}/actions/${encodeURIComponent(action)}`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '动作执行失败')
      setRuntime(data.state); setStatus(data.state.finished ? '试玩完成' : '试玩中 · 轮到 ' + data.state.current_player)
    } catch (err) { setError(err instanceof Error ? err.message : '动作执行失败') }
    finally { setBusy(false) }
  }

  async function exportGame() {
    if (!proposal || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/games/export`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(proposal) })
      if (!response.ok) throw new Error('导出失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url; link.download = `${String(proposal.game_id || 'pocker-game')}.pocker-game.zip`; link.click()
      URL.revokeObjectURL(url); setStatus('游戏包已导出')
    } catch (err) { setError(err instanceof Error ? err.message : '导出失败') }
    finally { setBusy(false) }
  }

  async function confirmRules() {
    if (!proposal || busy) return
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/agent/confirm`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ proposal, messages: turns.map(turn => ({ role: turn.role, content: turn.content })) }) })
      const data = await response.json()
      if (!response.ok || data.kind !== 'confirmed') throw new Error(data.errors?.join('\n') || data.detail || '规则确认失败')
      setConfirmed(true); setStatus('规则已确认 · 可以模拟')
    } catch (err) { setError(err instanceof Error ? err.message : '规则确认失败') }
    finally { setBusy(false) }
  }

  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">♠</span><div><strong>Pocker Agent</strong><small>规则设计工作台</small></div></div><div className="top-actions"><span className="status"><span className="dot" />{status}</span><button className="config-link" onClick={() => setShowConfig(!showConfig)}>模型设置</button></div></header>
    {showConfig && <section className="config-panel"><div><span className="kicker">MODEL CONFIGURATION</span><h2>连接你的模型</h2><p>Key 仅发送到当前本机 API 服务，关闭页面后不会写入浏览器。</p></div><div className="config-fields"><input type="password" value={apiKey} onChange={event => setApiKey(event.target.value)} placeholder="API Key" autoComplete="off" /><input value={baseUrl} onChange={event => setBaseUrl(event.target.value)} placeholder="Base URL" /><input value={model} onChange={event => setModel(event.target.value)} placeholder="Model" /><button className="primary" onClick={configureModel} disabled={!apiKey.trim() || busy}>保存配置</button></div></section>}
    <section className="hero"><p className="eyebrow">GAME DESIGN LOOP</p><h1>把一句玩法想法，变成一局可玩的牌局。</h1><p className="lede">描述规则，和 Agent 一起补全细节。确认后运行模拟，检查每一步牌局状态。</p></section>
    <section className="workspace">
      <div className="panel conversation"><div className="panel-head"><div><span className="kicker">01 / CLARIFY</span><h2>玩法对话</h2></div><Sparkles size={18} /></div><div className="thread">{turns.length === 0 && <div className="empty">从一句玩法描述开始。Agent 会追问玩家、牌组、动作和胜负条件。</div>}{turns.map((turn, index) => <div className={`bubble ${turn.role}`} key={index}><span>{turn.role === 'user' ? '你' : 'Agent'}</span><p>{turn.content}</p></div>)}</div><div className="composer"><textarea value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) askAgent() }} placeholder="描述你想设计的扑克牌游戏…" /><button onClick={askAgent} disabled={busy || !input.trim()} title="发送"><Send size={17} /></button></div></div>
      <div className="panel rules"><div className="panel-head"><div><span className="kicker">02 / CONTRACT</span><h2>规则提案</h2></div>{proposal ? <span className={`pill ${confirmed ? 'ready' : ''}`}>{confirmed ? <><Check size={13} />已确认</> : '待确认'}</span> : <span className="pill">未生成</span>}</div>{proposal ? <><pre className="dsl">{JSON.stringify(proposal, null, 2)}</pre><div className="rule-actions"><button className="primary" onClick={confirmRules} disabled={busy || confirmed}><Check size={16} />{confirmed ? '规则已确认' : '确认规则'}</button><button className="secondary" onClick={simulate} disabled={busy || !confirmed}><Play size={16} />运行模拟</button></div></> : <div className="empty tall">完成一轮对话后，结构化规则会显示在这里。</div>}</div>
      <div className="panel trace"><div className="panel-head"><div><span className="kicker">03 / SIMULATION</span><h2>模拟轨迹</h2></div><span className="pill">{events.length ? `${events.length} events` : '等待运行'}</span></div>{error && <div className="error"><CircleAlert size={16} /><pre>{error}</pre></div>}{events.length ? <div className="events">{events.map((event, index) => <div className="event" key={index}><span className="event-index">{String(index + 1).padStart(2, '0')}</span><div><strong>{String(event.event)}</strong><code>{JSON.stringify(event, null, 2)}</code></div></div>)}</div> : <div className="empty tall">模拟完成后，这里会展示发牌、动作、状态变化和结果。</div>}</div>
      <div className="panel runtime"><div className="panel-head"><div><span className="kicker">04 / PLAY</span><h2>单人试玩</h2></div><span className="pill">{runtime ? (runtime.finished ? '已结束' : runtime.current_player) : '未开始'}</span></div>{!runtime ? <div className="empty tall"><button className="primary" onClick={startRuntime} disabled={!confirmed || busy}><Play size={16} />开始试玩</button></div> : <><div className="table"><div className="table-label">桌面</div>{runtime.table.length ? runtime.table.map((card, index) => <span className="card" key={index}>{card.rank}{card.suit}</span>) : <span className="muted">尚无出牌</span>}</div><div className="hands">{runtime.players.map(player => <div className="hand" key={player.id}><span>{player.id}</span><div>{player.hand.map((card, index) => <span className="card" key={index}>{card.rank}{card.suit}</span>)}</div></div>)}</div><div className="actions">{runtime.legal_actions.map(action => <button className="primary" key={action} onClick={() => playAction(action)} disabled={busy}>{action}</button>)}</div></>}</div>
      <div className="export-bar"><div><span className="kicker">05 / EXPORT</span><strong>把这局游戏带走</strong><span>下载 DSL 和通用运行时可加载的游戏包。</span></div><button className="primary" onClick={exportGame} disabled={!proposal || busy}>下载游戏包</button></div>
    </section>
  </main>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
