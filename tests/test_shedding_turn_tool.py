from pocker_agent.tools import CardRef, SheddingTurnTool


def c(rank, suit): return CardRef(rank + suit, rank, suit, 1)


def test_shedding_turn_mutates_shared_state_and_finishes():
    card = c("7", "S")
    state = {"hands": [[card], [c("8", "H")]], "table": [c("2", "S")], "current_player": 0}
    result = SheddingTurnTool().play(state, "play", card_index=0)
    assert result["finished"] and state["winners"] == [0]
