from pocker_agent.assets import CardAssetRegistry
from pocker_agent.game_layer import GameLayer
from pocker_agent.tools import DeckTool
from pocker_agent.tools import CardRef, PotTool, best_of, beats, classify
from pocker_agent.tools import ToolPlan, plan_for_rules


def test_deck_tool_is_deterministic_and_deals_kitty():
    tool = DeckTool(["A", "K"], ["S", "H"], copies=1)
    first = tool.deal(seed=7, hands=2, cards_each=1, kitty=1).value
    second = tool.deal(seed=7, hands=2, cards_each=1, kitty=1).value
    assert [[c.id for c in h] for h in first["hands"]] == [[c.id for c in h] for h in second["hands"]]
    assert len(first["kitty"]) == 1


def test_game_layer_configures_registered_deck_tool():
    layer = GameLayer({"game_kind": "demo", "players": 2, "tools": [
        {"name": "deck", "ranks": ["A"], "suits": ["S", "H"]}
    ]}).configure()
    assert layer.describe()["configured"]
    assert isinstance(layer.tools["deck"], DeckTool)


def test_asset_registry_uses_existing_svg_and_fallbacks():
    registry = CardAssetRegistry()
    assert registry.asset("AS") == "/assets/cards/ace_of_spades.svg"
    assert registry.asset("jokerX") is None


def test_holdem_ranking_and_side_pots_are_reusable_tools():
    cards = [CardRef("A"+s, "A", s, 14) for s in ["S", "H", "D", "C"]] + [CardRef("KS", "K", "S", 13)]
    assert best_of(cards)[0] == 7  # four of a kind
    pot = PotTool([0, 0, 0])
    pot.committed = [100, 50, 200]
    assert pot.pots()[0]["amount"] == 150
    assert pot.pots()[1]["amount"] == 100
    assert pot.distribute({0: [2], 1: [0]}) == [100, 0, 250]


def test_doudizhu_classifier_handles_rocket_bomb_and_following():
    cards = [CardRef("BJ", "BJ", "", 15), CardRef("RJ", "RJ", "", 16)]
    rocket = classify(cards)
    bomb = classify([CardRef("7"+s, "7", s, 7) for s in ["S", "H", "D", "C"]])
    assert rocket.kind == "rocket"
    assert bomb.kind == "bomb"
    assert beats(bomb, classify([CardRef("AS", "A", "S", 14)]))
    four_two = classify([CardRef("9"+s, "9", s, 9) for s in "SHDC"] + [CardRef("3S", "3", "S", 3), CardRef("4S", "4", "S", 4)])
    assert four_two.kind == "four_with_two"
    triple_single = classify([CardRef("6"+s, "6", s, 6) for s in "SHD"] + [CardRef("9C", "9", "C", 9)])
    triple_pair = classify([CardRef("8"+s, "8", s, 8) for s in "SHD"] + [CardRef("KC", "K", "C", 13), CardRef("KH", "K", "H", 13)])
    assert triple_single.kind == "triple_single" and triple_pair.kind == "triple_pair"


def test_tool_plan_is_the_agent_facing_composition_contract():
    plan = ToolPlan(game_kind="holdem", players=3, tools=[
        {"name": "deck", "config": {"ranks": ["A"], "suits": ["S", "H", "D"]}}
    ])
    layer = GameLayer.from_plan(plan)
    assert layer.describe() == {"game_kind": "holdem", "tools": ["deck"], "players": 3, "configured": True}


def test_existing_rules_can_emit_a_composition_plan():
    from pocker_agent.game_rules import BlackjackRule
    rule = BlackjackRule(schema_version="0.2", game_id="bj", title="21", deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]}, players={"min_players":2,"max_players":2,"starting_hand_size":2}, max_rounds=1, kind="blackjack", target=21, dealer_stand_on=17, dealer_hits_soft_17=False, natural_beats_21=True, dealing="fresh_deck_each_round", betting=False)
    assert plan_for_rules(rule)["tools"][0]["name"] == "deck"
