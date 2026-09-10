from pocker_agent.tools import DeckTool, best_of

def test_standard_deck_uses_ace_high_values():
    cards = DeckTool(["A","K","Q","J","10"],["S"]).cards()
    assert cards[0].value == 14
    same_suit = [c for c in DeckTool(["A","K","Q","J","10"],["S","H"]).cards() if c.suit == "S"]
    assert best_of(same_suit)[0] == 8
