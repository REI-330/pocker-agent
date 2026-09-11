import type {ConversationSnapshot} from '../../shared/api/types'
export function RulesPanel({snapshot, canConfirm, confirming, onConfirm}: {snapshot: ConversationSnapshot | null; canConfirm: boolean; confirming: boolean; onConfirm: () => void}) {
  const draft = snapshot?.draft
  const proposal = snapshot?.proposal
  return <section className="panel rules"><div className="panel-head"><div><span className="kicker">02 / RULES</span><h2>规则提案</h2></div><span className={'pill ' + (proposal ? 'ready' : '')}>{proposal ? '已生成' : draft ? '待确认' : '设计中'}</span></div>
    {draft ? <div className="rule-summary"><h3>{draft.title}</h3><p>{draft.summary}</p>{proposal && <><p className="support-note">规则已通过服务端验证，可开始生成游戏。</p><details><summary>查看完整规则 DSL</summary><pre className="dsl">{JSON.stringify(proposal, null, 2)}</pre></details></>}
      <div className="rule-actions"><button className="primary" onClick={onConfirm} disabled={!canConfirm || confirming}>{confirming ? '正在生成…' : '确认规则并生成游戏'}</button></div></div>
      : <div className="empty tall">继续和 Agent 对话，确认玩法细节后会出现规则摘要。</div>}
  </section>
}
