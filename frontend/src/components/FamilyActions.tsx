import {useState} from 'react'
import {type ActionArguments, type Runtime} from '../api'

const labels: Record<string,string> = {play:'出牌',draw:'摸牌',discard:'弃牌',pass:'跳过',hit:'要牌',stand:'停牌',fold:'弃牌',check:'过牌',call:'跟注',raise:'加注',all_in:'全下',showdown:'摊牌',next_round:'下一题 / 下一轮'}
const suitNames: Record<string,string> = {S:'黑桃 ♠', H:'红桃 ♥', D:'方块 ♦', C:'梅花 ♣'}

export function FamilyActions({state, busy, index, act}: {
  state: Runtime; busy: boolean; index: number;
  act: (action: string, index: number, args?: ActionArguments) => void;
}) {
  const [expression, setExpression] = useState('')
  const [suit, setSuit] = useState('S')
  const [raiseAmount, setRaiseAmount] = useState('')
  const arithmetic = state.legal_actions.includes('submit_expression')
  if (state.kind === 'plugin') return <div className="game-controls"><div className="actions">{state.plugin_actions?.map(action =>
    <button className="primary" key={action.id} disabled={busy} onClick={() => act(action.id,0)}
      aria-label={action.label}>{action.target_player != null ? '🂠 ' : ''}{action.label}</button>)}</div></div>
  return <div className="game-controls">
    {arithmetic && <form className="expression-form" onSubmit={e => {e.preventDefault(); if (!busy && expression.trim()) act('submit_expression',0,{expression})}}>
      <label htmlFor="expression">输入算式</label>
      <div className="expression-input"><input id="expression" value={expression} onChange={e => setExpression(e.target.value)} disabled={busy} autoComplete="off" spellCheck={false} placeholder="例如 (8 / (3 - 8 / 3))" maxLength={256}/>
        <button className="primary" type="submit" disabled={busy || !expression.trim()}>提交答案</button></div>
      <p className="muted-instructions">用牌面对应的数字输入，可使用括号；× 和 ÷ 也可以。</p>
    </form>}
    {state.kind === 'shedding' && state.wild_rank && state.players[0].hand[index]?.rank === state.wild_rank && <label className="suit-choice">万能牌指定花色
      <select value={suit} onChange={e => setSuit(e.target.value)} disabled={busy}>{state.suit_options?.map(s => <option key={s} value={s}>{suitNames[s] || s}</option>)}</select>
    </label>}
    <div className="actions">{state.legal_actions.filter(a => a !== 'submit_expression').map(action => <button className={['give_up','no_solution'].includes(action)?'secondary':'primary'} key={action}
      onClick={() => act(action,index,{declared_suit:suit, amount: action === 'raise' && raiseAmount ? Number(raiseAmount) : undefined})} disabled={busy || (action === 'raise' && (!raiseAmount || Number(raiseAmount) <= 0)) || (action === 'play' && !!state.legal_card_indices && !state.legal_card_indices.includes(index))}>
      {action === 'give_up' ? '放弃并看答案' : action === 'no_solution' ? '我认为无解' : action === 'next_round' ? (state.kind === 'arithmetic' ? '下一题' : '下一轮') : labels[action] || action}
    </button>)}</div>
    {state.kind === 'holdem' && state.legal_actions.includes('raise') && <label className="raise-choice">加注到（总投入）
      <input type="number" min="1" step="1" value={raiseAmount} onChange={e => setRaiseAmount(e.target.value)} disabled={busy} placeholder="输入金额" />
    </label>}
  </div>
}
