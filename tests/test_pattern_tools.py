import pytest
from pocker_agent.tools import CardRef, detect_meld, resolve_trick, ToolError

def c(rank, suit): return CardRef(rank+suit, rank, suit, 0)

def test_trick_resolve_honors_trump_and_lead():
    cards = [c("10", "H"), c("A", "H"), c("2", "S")]
    assert resolve_trick(cards)["winner_index"] == 1
    assert resolve_trick(cards, trump="S")["winner_index"] == 2

def test_meld_detects_set_and_run_without_wrap():
    assert detect_meld([c("7","S"), c("7","H"), c("7","D")])["kind"] == "set"
    assert detect_meld([c("4","S"), c("5","S"), c("6","S")])["kind"] == "run"
    assert not detect_meld([c("K","S"), c("A","S"), c("2","S")])["valid"]

def test_pattern_tools_reject_duplicate_ids():
    with pytest.raises(ToolError): resolve_trick([c("A","S"), c("A","S")])
