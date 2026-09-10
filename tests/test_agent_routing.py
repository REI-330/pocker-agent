from pocker_agent.agent import RuleAgent


def test_new_game_families_have_fail_closed_routing():
    assert RuleAgent._expected_family("做一个斗地主") == "doudizhu"
    assert RuleAgent._expected_family("做一个德州扑克盲注游戏") == "holdem"
