from pocker_agent.engine import RuleEngine, build_deck
from pocker_agent.models import GameRuleDSL
from pocker_agent.simulation import simulate


def rules() -> GameRuleDSL:
    return GameRuleDSL.model_validate(
        {
            "game_id": "high-card",
            "title": "High Card",
            "description": "Draw one card and keep the highest card.",
            "deck": {"suits": ["S", "H"], "ranks": ["A", "K", "Q", "J"]},
            "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 1},
            "actions": [{"name": "play", "source": "hand"}],
            "phases": [{"name": "main", "actions": ["play"], "max_turns": 2}],
            "max_rounds": 1,
        }
    )


def test_deck_contains_each_card_combination():
    assert len(build_deck(rules())) == 8


def test_simulation_completes_and_emits_trace():
    result = simulate(rules(), seed=7)
    assert result.completed is True
    assert result.winner in {"player-1", "player-2"}
    assert [event["event"] for event in result.events][:2] == ["game_started", "card_drawn"]


def test_same_seed_is_deterministic():
    first = simulate(rules(), seed=42)
    second = simulate(rules(), seed=42)
    assert first.events == second.events


def test_illegal_action_is_rejected():
    engine = RuleEngine(rules(), seed=1)
    engine.setup()
    try:
        engine.step("draw")
    except ValueError as error:
        assert str(error) == "illegal_action:draw"
    else:
        raise AssertionError("illegal action was accepted")
