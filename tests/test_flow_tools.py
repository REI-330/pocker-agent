from pocker_agent.tools import CardRef, DrawDiscardTool, TriggerTool, climb_beats

def c(rank): return CardRef(rank+'S', rank, 'S', 0)

def test_draw_discard_and_recycle():
    hand=[]; tool=DrawDiscardTool([c('A')]); tool.draw(hand); tool.discard_cards(hand,[c('A')]); tool.draw(hand, recycle=True)
    # The visible top cannot be recycled; it remains on the table.
    assert hand == [] and tool.top() == c('A')

def test_climbing_and_triggers():
    assert climb_beats({'kind':'bomb','rank':3},{'kind':'single','rank':14})
    t=TriggerTool(); seen=[]; t.on('play',lambda p: seen.append(p['card'])); t.emit('play',{'card':'AS'})
    assert seen == ['AS']
