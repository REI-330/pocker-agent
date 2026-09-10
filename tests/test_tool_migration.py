from pocker_agent.engine import Card
from pocker_agent.executors import create_engine
from pocker_agent.game_rules import parse_rule


def rules_for(kind):
    payload = {
        "schema_version": "0.2", "kind": kind, "game_id": "migration-" + kind,
        "title": "Migration", "deck": {"suits": ["S", "H", "D", "C"],
        "ranks": ["A", *map(str, range(2, 11)), "J", "Q", "K"]},
        "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 2},
        "max_rounds": 1,
    }
    if kind == "blackjack":
        payload.update(target=21, dealer_stand_on=17, dealer_hits_soft_17=False,
                       natural_beats_21=True, dealing="fresh_deck_each_round", betting=False)
    else:
        payload.update(match="suit_or_rank", wild_rank="8", draw_policy="until_playable",
                        recycle_discard=True, blocked_result="draw",
                        players={"min_players": 2, "max_players": 2, "starting_hand_size": 5})
    return parse_rule(payload)


def test_blackjack_settlement_requests_registered_hand_rank_tool():
    engine = create_engine(rules_for("blackjack"), seed=7)
    engine.setup()
    calls = []
    original = engine.tool_registry.create

    def create(name, **config):
        calls.append(name)
        return original(name, **config)

    engine.tool_registry.create = create
    engine.state.players[0].hand = [Card("H", "10", 10), Card("H", "7", 7)]
    engine.state.players[1].hand = [Card("S", "9", 9), Card("S", "7", 7)]
    engine.state.deck = [Card("D", "2", 2)]
    engine.state.phase = "要牌或停牌"
    engine.state.finished = False
    engine.step("stand")
    assert "hand_rank" in calls


def test_shedding_uses_registered_match_draw_and_turn_tools():
    engine = create_engine(rules_for("shedding"), seed=7)
    engine.setup()
    engine.discard = [Card("H", "K", 13)]
    engine.state.table = list(engine.discard)
    engine.extra["active_suit"] = "H"
    engine.state.players[0].hand = [Card("H", "5", 5), Card("S", "6", 6)]
    calls = []
    original = engine.tool_registry.create

    def create(name, **config):
        calls.append(name)
        return original(name, **config)

    engine.tool_registry.create = create
    engine.step("play", 0)
    assert {"card_match", "draw_discard", "turn_order"} <= set(calls)
