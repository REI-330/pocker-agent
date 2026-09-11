from pocker_agent.runtime import ToolPlanRuntime


def test_runtime_executes_phase_outcome_and_settlement_actions():
    plan = {
        "game_kind": "generic",
        "players": 2,
        "tools": [
            {"name": "phase_progress", "config": {"phases": ["one", "two"]}},
            {"name": "winner_resolve"},
            {"name": "score_settle"},
        ],
        "actions": [
            {"tool": "phase_progress", "operation": "advance", "result_key": "phase"},
            {"tool": "winner_resolve", "operation": "call", "args": {"values": [2, 5]}, "result_key": "winners"},
            {"tool": "score_settle", "operation": "call", "args": {"scores": [0, 0], "winners": "$state.winners", "points": 1}, "result_key": "scores"},
        ],
    }
    runtime = ToolPlanRuntime(plan)
    result = runtime.execute_actions()
    assert result["state"]["phase"]["phase"] == "two"
    assert result["state"]["winners"] == [1]
    assert result["state"]["scores"] == [0, 1]
    assert len([e for e in result["events"] if e["event"] == "tool_called"]) == 3
