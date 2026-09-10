from pocker_agent.oracle import run_golden_traces


def test_independent_golden_traces_pass():
    result = run_golden_traces()
    assert result and all(result.values()), result
