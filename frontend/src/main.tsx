import React, {useCallback, useEffect, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {API, request, downloadGame, messageOf, type Message, type Rule, type Runtime, type GameEvent, type ModelConfig, type ActionArguments} from './api'
import {ModelSettings} from './components/ModelSettings'
import {GameTable} from './components/GameTable'
import './styles.css'
import './runtime.css'
import './config.css'

type Verification = {scenario?:{status:string;cases:string[]};properties?:{status:string;checks:string[]};independent_oracle?:{status:string;message:string};browser?:{status:string;message:string}}
type TurnResult = {kind:string;message:string;rules:Rule|null;errors:string[];messages:Message[];facts:string[];tool_plan?:Record<string,unknown>;tool_plan_source?:string;contract?:{semantic_oracle:string};build?:{attempt:number;status:string;error?:string;checks?:string[];verification?:Verification}[]}
type BuildJob = {id:string;status:string;progress:{message:string;time:number}[];result:TurnResult|null;error:string|null}
type Workbench = {turns: Message[]; messages: Message[]; proposal: Rule | null; toolPlan: Record<string,unknown>|null; confirmed: boolean; events: GameEvent[]; runtimeId: string | null; facts: string[]; pending: {id:string;content:string}|null; buildLog:string[]}
const EMPTY: Workbench = {turns:[],messages:[],proposal:null,toolPlan:null,confirmed:false,events:[],runtimeId:null,facts:[],pending:null,buildLog:[]}
const STORAGE_KEY = 'pocker-workbench-v2'
function restore(): {work: Workbench; error: string} {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (!data) return {work:EMPTY,error:''}
    if (!Array.isArray(data.turns) || !Array.isArray(data.messages) || !Array.isArray(data.events)) throw new Error()
    return {work:{...EMPTY,...data},error:''}
  } catch { return {work:EMPTY,error:'本机草稿无法读取，已打开空白工作台'} }
}
function App() {
  const [initial] = useState(restore)
  const [work, setWork] = useState(initial.work)
  const [input,setInput] = useState(initial.work.pending?.content ?? (initial.work.turns.length ? '' : '我想做一个两人比大小游戏，每人一张牌，翻开后点数高的人获胜。'))
  const [runtime,setRuntime] = useState<Runtime | null>(null)
  const [busy,setBusy] = useState(initial.work.pending ? '恢复生成任务' : initial.work.runtimeId ? '恢复牌局' : '')
  const [error,setError] = useState(initial.error)
  const [status,setStatus] = useState('描述玩法，开始设计')
  const [showConfig,setShowConfig] = useState(true)
  const [modelConfig,setModelConfig] = useState<ModelConfig | null>(null)
  const [configBlocked,setConfigBlocked] = useState(true)
  const blocked = !!busy || !!work.pending
  const onSaved = useCallback((data: ModelConfig) => setModelConfig(data), [])

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(work)) }
    catch { setError('浏览器无法保存草稿；请允许此站点使用本机存储') }
  }, [work])
  useEffect(() => {
    if (!initial.work.runtimeId || initial.work.pending) return
    let active = true
    request<Runtime>('/api/runtime/sessions/' + initial.work.runtimeId)
      .then(data => { if (active) {setRuntime(data);setStatus('已恢复上次牌局')} })
      .catch(err => { if (active) setError(messageOf(err)) })
      .finally(() => { if (active) setBusy('') })
    return () => {active = false}
  }, [initial])

  useEffect(() => {
    if (!work.pending) return
    const pending = work.pending
    let active = true
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const job = await request<BuildJob>('/api/agent/jobs/' + pending.id)
        if (!active) return
        const log = job.progress.map(p=>p.message)
        setWork(current=>({...current,buildLog:log}))
        if (job.status === 'running') {
          setBusy(log[log.length-1] || '生成游戏')
          timer = setTimeout(()=>void poll(),1000)
          return
        }
        if (job.status === 'failed' || !job.result) {
          setError(job.error || '生成任务失败')
          setStatus('生成失败，可修改规则或重试')
          setWork(current=>({...current,pending:null}))
        } else {
          const data = job.result
          const attemptLog = (data.build || []).map(a=>`第 ${a.attempt} 次代码：${a.status === 'passed' ? '固定场景与独立属性检查通过（语义 oracle：' + (a.verification?.independent_oracle?.status === 'passed' ? '通过' : '未提供') + '；浏览器：' + (a.verification?.browser?.status === 'passed' ? '通过' : '未验收') + '）' : a.error}`)
          setWork(current=>({...current,turns:[...current.turns,{role:'user',content:pending.content},{role:'assistant',content:data.message}],
            messages:data.messages,proposal:data.rules,toolPlan:data.tool_plan || null,confirmed:false,events:[],runtimeId:null,facts:data.facts || [],pending:null,buildLog:[...log,...attemptLog]}))
          setRuntime(null);setInput('')
          if(data.kind === 'error') setError([data.message,...data.errors].join('\n'))
          setStatus(data.kind === 'question' ? '等待补充规则' : data.kind === 'unsupported' ? '当前实现协议尚不支持' : data.kind === 'error' ? '生成未通过测试' : '规则已生成，请确认')
        }
        setBusy('')
      } catch(err) {
        if (!active) return
        setError(messageOf(err))
        if(messageOf(err).includes('生成任务已失效')) {
          setWork(current=>({...current,pending:null}));setBusy('');return
        }
        // Keep the task ID on transport failure; refreshing can resume polling.
        setBusy('等待生成任务连接恢复')
        timer = setTimeout(()=>void poll(),3000)
      }
    }
    void poll()
    return ()=>{active=false;clearTimeout(timer)}
  }, [work.pending?.id])

  async function operation(label: string, task: () => Promise<void>) {
    if (blocked) return
    setBusy(label);setError('')
    try { await task() } catch (err) {setError(messageOf(err))}
    finally {setBusy('')}
  }
  function ask() {
    if (!input.trim() || !modelConfig?.configured || configBlocked) return
    void operation('生成规则', async () => {
      const content = input.trim()
      const job = await request<BuildJob>('/api/agent/jobs', {
        message: content, messages: work.messages, proposal: work.proposal,
      })
      setWork({...work,pending:{id:job.id,content},buildLog:[]})
      setStatus('生成任务已启动')
    })
  }
  function confirmRules() {
    if (!work.proposal) return
    void operation('确认规则', async () => {
      const data = await request<{kind:string;rules:Rule;errors:string[];facts:string[];tool_plan?:Record<string,unknown>}>('/api/agent/confirm',{proposal:work.proposal,tool_plan:work.toolPlan})
      if (data.kind !== 'confirmed') throw new Error(data.errors.join('\n'))
      setWork({...work,proposal:data.rules,toolPlan:data.tool_plan || work.toolPlan,confirmed:true,facts:data.facts});setStatus('规则已确认')
    })
  }
  function simulate() {
    if (!work.confirmed || !work.proposal) return
    void operation('运行模拟', async () => {
      const data = await request<{completed:boolean;events:GameEvent[]}>('/api/simulations?seed=7',work.proposal)
      if (!data.completed) throw new Error('模拟尚未完成')
      setWork({...work,events:data.events});setStatus('模拟完成，所有回合已执行')
    })
  }
  function start() {
    if (!work.confirmed || !work.proposal) return
    void operation('开始试玩', async () => {
      const data = await request<Runtime>('/api/runtime/sessions', {rules:work.proposal,tool_plan:work.toolPlan})
      setRuntime(data);setWork({...work,runtimeId:data.session_id});setStatus(data.finished ? '本局已结束' : '轮到你出牌')
    })
  }
  function act(action: string, cardIndex: number, args: ActionArguments = {}) {
    if (!runtime || !work.confirmed) return
    void operation('执行回合', async () => {
      const data = await request<{state:Runtime}>('/api/runtime/sessions/' + runtime.session_id + '/actions/' + action,{
        revision:runtime.revision,card_index:cardIndex,...args,
      })
      setRuntime(data.state);setStatus(data.state.finished ? '本局结束，可以再来一局' : '等待你的下一步操作')
    })
  }
  function refresh() {
    const id = runtime?.session_id || work.runtimeId
    if (!id) return
    void operation('刷新牌局', async () => {setRuntime(await request<Runtime>('/api/runtime/sessions/' + id));setStatus('牌局已刷新')})
  }
  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">♠</span><div><strong>Pocker Agent</strong><small>把规则变成牌局</small></div></div>
      <div className="top-actions"><span className="status" role="status">{busy ? '正在' + busy + '…' : status}</span>
      <button className="config-link" onClick={() => setShowConfig(!showConfig)}>{showConfig ? '收起模型设置' : '模型设置'}</button></div>
    </header>
    <div hidden={!showConfig}><ModelSettings onSaved={onSaved} onBlockedChange={setConfigBlocked} disabled={blocked} /></div>
    {error && <div className="error" role="alert"><pre>{error}</pre></div>}
    <section className="hero"><p className="eyebrow">FROM IDEA TO PLAY</p><h1>写下规则。<br/>开始一局。</h1><p className="lede">和 Agent 一起补全玩法，确认规则，查看模拟，再与电脑试玩。</p>
      <p className="support-note">已有玩法复用规则引擎。代码生成仍在实验阶段：Agent 编写新玩法逻辑，测试通过后才提供试玩，可能生成失败。</p></section>
    <section className="workspace">
      <section className="panel conversation"><div className="panel-head"><div><span className="kicker">01 / DESIGN</span><h2>玩法对话</h2></div><button className="secondary" disabled={blocked} onClick={() => {setWork(EMPTY);setRuntime(null);setError('');setStatus('已开始新的设计')}}>新建游戏</button></div>
        <div className="thread">{!work.turns.length && <p className="empty">例如：两人比大小，使用标准 52 张牌，A 最大。每轮各出一张，最高牌得 1 分，平局各得 1 分，共 3 轮。</p>}
          {work.turns.map((turn,i) => <div className={'bubble ' + turn.role} key={i}><span>{turn.role === 'user' ? '你' : 'Agent'}</span><p>{turn.content}</p></div>)}
        </div>
        <div className="composer"><textarea aria-label="玩法描述" value={input} onChange={e => setInput(e.target.value)} disabled={blocked} placeholder="描述规则或回答 Agent 的问题…" /><button onClick={ask} disabled={blocked || configBlocked || !input.trim() || !modelConfig?.configured}>发送</button></div>
        {!!work.buildLog.length && <details open={!!work.pending} className="build-progress"><summary>{work.pending ? '游戏生成进度' : '查看生成与测试记录'}</summary><ol>{work.buildLog.map((line,i)=><li key={i}>{line}</li>)}</ol></details>}
        {!modelConfig?.configured && <p className="support-note">请先在模型设置中保存配置。</p>}
        {modelConfig?.configured && configBlocked && <p className="support-note">模型配置正在处理或有未保存的修改，请在模型设置中完成保存或撤销。</p>}
      </section>
      <section className="panel rules"><div className="panel-head"><div><span className="kicker">02 / RULES</span><h2>规则提案</h2></div><span className="pill">{work.confirmed ? '已确认' : '待确认'}</span></div>
        {work.proposal ? <><div className="rule-summary"><h3>{work.proposal.title}</h3><p>{work.proposal.players.min_players} 位玩家 · {work.proposal.max_rounds} 轮</p><ul className="rule-facts">{work.facts.map((fact,i)=><li key={i}>{fact}</li>)}</ul><p className="support-note">请逐条核对可执行定义后确认；代码生成玩法的语义 oracle 仍需人工独立验收。</p></div>
        <details><summary>查看完整规则 DSL</summary><pre className="dsl">{JSON.stringify(work.proposal,null,2)}</pre></details>
        {work.proposal.source && <details><summary>查看 Agent 编写的游戏代码</summary><pre className="dsl">{work.proposal.source}</pre></details>}
        <div className="rule-actions"><button className="primary" onClick={confirmRules} disabled={blocked || work.confirmed}>确认规则</button><button className="secondary" onClick={simulate} disabled={blocked || !work.confirmed}>运行模拟</button></div></> : <div className="empty tall">确认玩法细节后，这里会出现规则提案。</div>}
      </section>
      <section className="panel trace"><div className="panel-head"><div><span className="kicker">03 / VERIFY</span><h2>模拟轨迹</h2></div><span className="pill">{work.events.length} 个事件</span></div>
        {work.events.length ? <div className="events">{work.events.map((event,i) => <div className="event" key={i}><span className="event-index">{i+1}</span><div><strong>{String(event.event)} · 第 {String(event.round)} 轮</strong><code>{JSON.stringify(event)}</code></div></div>)}</div> : <p className="empty tall">运行模拟检查发牌、电脑动作、轮次计分和结果。</p>}
      </section>
      <GameTable state={runtime} busy={blocked} canStart={work.confirmed} start={start} act={act} refresh={refresh}/>
      <section className="export-bar"><div><span className="kicker">05 / TAKE IT WITH YOU</span><h2>把这局游戏带走</h2><p>{work.proposal?.kind ? '当前玩法支持网页试玩和保存恢复，离线导出尚未支持。' : '解压后打开 index.html 离线游玩。练习局固定发牌，无需 API Key。'}</p></div>
        <button className="primary" disabled={blocked || !work.confirmed || !!work.proposal?.kind} onClick={() => void operation('导出游戏',async () => {await downloadGame(work.proposal!);setStatus('游戏包已下载，解压后打开 index.html')})}>下载游戏包</button>
      </section>
    </section>
    <footer>牌面素材：<a href="https://github.com/hayeah/playing-cards-assets" target="_blank" rel="noreferrer">Playing Cards Assets</a> · <a href={API + '/assets/cards/LICENSE'}>MIT License</a></footer>
  </main>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
