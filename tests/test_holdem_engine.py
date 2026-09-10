from pocker_agent.executors import create_engine
from pocker_agent.game_rules import HoldemRule
from pocker_agent.simulation import simulate

def rule():
    return HoldemRule(schema_version="0.2",game_id="holdem",title="德州",deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},players={"min_players":2,"max_players":2,"starting_hand_size":2},max_rounds=1,kind="holdem")

def test_holdem_setup_blinds_and_view():
    e=create_engine(rule(),seed=3); e.setup(); v=e.view()
    assert len(v["board"])==0 and v["pot"]==30 and v["players"][0]["hidden_count"]==0
    assert "call" in e.legal_actions()


def test_holdem_simulation_reaches_river_and_declares_winner():
    result = simulate(rule(), seed=11, max_steps=100)
    assert result.completed and result.winner in {0, 1}
    assert any(event["event"] == "street_started" and event["street"] == "river" for event in result.events)
    engine = create_engine(rule(), seed=11); engine.run(max_steps=100)
    assert sum(engine.state.stacks) == 2000

def test_holdem_raise_amount_and_all_in_reaches_showdown():
    e = create_engine(rule(), seed=5); e.setup()
    before = e.state.committed[0]
    e.step("raise", amount=100)
    assert e.state.committed[0] == 100 and e.state.committed[0] > before
    e.step("all_in")
    e.step("all_in")
    for _ in range(10):
        if e.state.finished: break
        e.step("check")
    assert e.state.finished and e.state.winners
    assert sum(e.state.stacks) == 2000

def test_holdem_rejects_raise_beyond_stack_without_mutation():
    e = create_engine(rule(), seed=5); e.setup()
    committed = list(e.state.committed); stacks = list(e.state.stacks)
    try:
        e.step("raise", amount=10_000)
    except ValueError:
        pass
    else:
        raise AssertionError("oversized raise was accepted")
    assert e.state.committed == committed and e.state.stacks == stacks
