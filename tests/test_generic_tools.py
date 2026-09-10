from pocker_agent.tools import CardRef, DeckTool, ZoneTool, TurnOrderTool, evaluate, follow_suit, group_by, matches
from pocker_agent.tools.registry import default_registry

def test_zone_move_visibility_and_matching():
    cards = DeckTool(["A", "K"], ["S", "H"]).cards()
    zones = ZoneTool(); zones.create("deck", cards); zones.create("hand", visible_to={"p1"})
    zones.move("deck", "hand", count=1)
    assert len(zones.view("hand", "p1")) == 1 and zones.view("deck", "p2")[0]["hidden"]
    assert matches(cards[0], cards[1], fields=("rank",))

def test_turn_order_and_generic_conditions():
    order = TurnOrderTool(["a", "b", "c"])
    assert order.current_player() == "a"
    order.reverse(); order.advance(); assert order.current_player() == "c"
    assert evaluate("hand_empty", hand_size=0)
    assert evaluate("passes_reached", passes=2, target=2)

def test_matching_helpers_and_registry():
    cards = DeckTool(["A", "2"], ["S", "H"]).cards()
    assert follow_suit(cards, cards[0], card=cards[0])
    assert set(group_by(cards, "rank")) == {"A", "2"}
    names = default_registry().names()
    assert {"zones", "card_match", "follow_suit", "group_cards", "condition"} <= set(names)
