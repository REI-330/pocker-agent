from pocker_agent.tools import doudizhu_multiplier, doudizhu_scores

def test_doudizhu_scoring_multiplier_and_team_zero_sum():
    assert doudizhu_multiplier(3, bombs=1, rocket=True, spring=True) == 24
    scores = doudizhu_scores(3, landlord=0, winner=1, bombs=1)
    assert scores == [-12, 6, 6] and sum(scores) == 0
