from pocker_agent.tools.core import CardRef
from pocker_agent.tools.draw_discard import DrawUntilPlayableTool

def c(i,r,s): return CardRef(f'{i}{s}',r,s, int(r) if r.isdigit() else 0)
def test_draw_until_playable_stops_on_matching_card():
    hand=[]; stock=[c('2','9','H'),c('1','4','S')]; discard=[c('0','4','H')]
    result=DrawUntilPlayableTool(recycle=False).draw_until_playable(hand,stock,discard,top=discard[-1])
    assert result['playable'] and [x.rank for x in hand]==['4']

def test_draw_until_playable_reports_exhaustion():
    hand=[c('1','K','S')]; stock=[]; discard=[c('0','4','H')]
    result=DrawUntilPlayableTool(recycle=False).draw_until_playable(hand,stock,discard,top=discard[-1])
    assert result['playable'] is False and result['drawn']==[]
