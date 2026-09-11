from pocker_agent.tools import default_registry, resolve_winners, settle_scores


def test_outcome_tools_resolve_ties_and_scores():
    assert resolve_winners([10, 12, 12]) == [1, 2]
    assert resolve_winners([10, 8, 8], mode="min") == [1, 2]
    assert settle_scores([0, 2, 0], [1, 2], points=1) == [0, 3, 1]


def test_outcome_tools_are_registered_for_agent_plans():
    registry = default_registry()
    assert "winner_resolve" in registry.names()
    assert "score_settle" in registry.names()
    assert registry.create("winner_resolve")(values=[1, 3, 3]) == [1, 2]
