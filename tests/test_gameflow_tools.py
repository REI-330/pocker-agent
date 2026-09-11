from pocker_agent.tools import WinConditionTool, SettlementTool
from pocker_agent.tools.registry import default_registry

def test_win_conditions_and_settlement():
    t=WinConditionTool([{'type':'hand_empty'}])
    assert t.check({'hand_sizes': {'a':0,'b':2}})['winners']==['a']
    s=SettlementTool(3)
    assert s.settle([10,-5,-5])['scores']==[10,-5,-5]
    assert {'win_condition','settlement'} <= set(default_registry().names())

def test_settlement_conservation():
    import pytest
    with pytest.raises(Exception): SettlementTool(2).settle([1,0])
