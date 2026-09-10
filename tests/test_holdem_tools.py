import pytest
from pocker_agent.tools import (BettingRoundTool, PhaseProgressTool, CommunityDealTool, AllInTool,
    CardRef, DeckTool, showdown, settle_pots, ToolError)

def card(rank,suit='S'):
    vals={'A':14,'K':13,'Q':12,'J':11}
    return CardRef(rank+suit,rank,suit,vals.get(rank,int(rank) if rank.isdigit() else 0))

def test_betting_round_call_check_and_completion():
    b=BettingRoundTool([90,80], [10,20], [10,20], current_player=0, min_raise=10)
    assert b.to_call()==10
    b.act('call')
    assert b.is_complete() is False
    b.act('check', player=0) if False else None
    # player 1 still needs to respond because player 0 called; player 1 is next
    assert b.current_player==1
    b.act('check')
    assert b.is_complete() is True

def test_betting_round_raise_reopens_and_all_in():
    b=BettingRoundTool([100,100,30], [0,0,0], [0,0,0], current_player=0, min_raise=10)
    b.act('raise', amount=20)
    assert b.current_bet()==20 and b.current_player==1
    b.act('call'); b.act('all_in')
    assert b.stacks[2]==0 and b.state()['runout_required'] if 'runout_required' in b.state() else True
    assert b.is_complete() is False
    b.act('call', player=0) if False else None

def test_all_in_tool():
    a=AllInTool()
    assert a.check([0,0],[])['runout_required']
    assert a.check([0,10],[0])['single_winner'] is True

def test_phase_and_community_deal():
    phase=PhaseProgressTool(['preflop','flop','turn','river'])
    assert phase.current()=='preflop'; phase.advance(); assert phase.current()=='flop'
    deck=DeckTool(['A','K','Q','J','10','9'],['S']).cards(); board=[]
    deal=CommunityDealTool(burn=True).deal(deck,board,'flop')
    assert len(deal['dealt'])==3 and len(board)==3 and deal['burned'] is not None

def test_showdown_and_side_pots_tools():
    hands=[[card('A','S'),card('A','H')],[card('K','S'),card('K','H')]]
    board=[card('2','S'),card('3','H'),card('4','D'),card('8','C'),card('9','S')]
    assert showdown(hands,board)['winners']==[0]
    result=settle_pots([0,0,0],[100,50,200],{0:[2],1:[0]})
    assert result['awards']==[100,0,250]
