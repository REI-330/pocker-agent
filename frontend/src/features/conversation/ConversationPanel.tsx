import type {ConversationPhase, Message} from '../../shared/api/types'

const phaseLabels: Record<ConversationPhase, string> = {designing: '继续描述玩法', thinking: 'Agent 思考中', proposal_ready: '规则摘要待确认', building: '正在生成游戏', playable: '游戏已就绪', failed: '上次操作失败'}
export function ConversationPanel({messages, input, phase, loading, sending, canSend, onInput, onSend, onCancel, onNew}: {messages: Message[]; input: string; phase: ConversationPhase; loading: boolean; sending: boolean; canSend: boolean; onInput: (value: string) => void; onSend: () => void; onCancel: () => void; onNew: () => void}) {
  return <section className="panel conversation"><div className="panel-head"><div><span className="kicker">01 / DESIGN</span><h2>玩法对话</h2></div><button className="secondary" disabled={loading || sending} onClick={onNew}>新建游戏</button></div>
    <div className="thread">{!messages.length && <p className="empty">例如：两人比大小，使用标准 52 张牌，A 最大。每轮各出一张，最高牌得 1 分，共 3 轮。</p>}
      {messages.map((message, i) => <div className={'bubble ' + message.role} key={i}><span>{message.role === 'user' ? '你' : 'Agent'}</span><p>{message.content}</p></div>)}
      {sending && <p className="muted-instructions" role="status">Agent 正在回复，你可以继续编辑下一条消息。</p>}
    </div>
    <div className="composer"><textarea aria-label="玩法描述" value={input} onChange={event => onInput(event.target.value)} placeholder="描述规则或回答 Agent 的问题…" disabled={loading}/><div className="composer-actions"><button onClick={onSend} disabled={!canSend || !input.trim()}>发送</button>{(phase === 'thinking' || phase === 'building') && <button className="secondary" onClick={onCancel}>取消当前操作</button>}</div></div>
  </section>
}
