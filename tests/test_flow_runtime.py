from pocker_agent.flow_runtime import FlowRuntime


def test_tool_flow_owns_wait_action_and_state_transition():
    plan = {
        "game_kind": "generic", "players": 2,
        "tools": [{"name": "state"}],
        "flow": {
            "entry": "start", "initial": {"finished": False, "winners": [], "current_player": 0},
            "nodes": {
                "start": {"kind": "call", "next": "wait", "action": {"tool": "state", "operation": "update", "args": {"state": "$state", "values": {"phase": "play"}}}},
                "wait": {"kind": "wait", "inputs": {"finish": "finish"}},
                "finish": {"kind": "call", "next": "end", "action": {"tool": "state", "operation": "update", "args": {"state": "$state", "values": {"finished": True, "winners": [0]}}}},
                "end": {"kind": "end"},
            },
        },
    }
    runtime = FlowRuntime(type("Rules", (), {"model_dump": lambda self, **_: {"kind": "generic"}})(), seed=1, tool_plan=plan)
    runtime.setup()
    assert runtime.legal_actions() == ["finish"]
    runtime.step("finish")
    assert runtime.state.finished and runtime.view()["winners"] == ["player-1"]
