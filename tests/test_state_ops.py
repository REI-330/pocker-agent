from pocker_agent.tools import DealerPolicyTool, PointContestTool


def test_point_contest_excludes_bust_and_prioritizes_target():
    assert PointContestTool().resolve([21, 20], [2, 3], 21) == [0]
    assert PointContestTool().resolve([22, 19], [3, 2], 21, first_bust_loses=True) == [1]


def test_dealer_policy_draws_until_stand():
    class Rank:
        def __call__(self, hand):
            return {"total": sum(hand), "soft": False}
    stock, hand = [4, 3, 2], [8]
    result = DealerPolicyTool().play(stock, hand, Rank(), stand_on=17)
    assert result["total"] == 17 and result["draws"] == 3
