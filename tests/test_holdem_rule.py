from pocker_agent.game_rules import HoldemRule
from pocker_agent.tools.plans import plan_for_rules


def test_holdem_rule_emits_composable_plan():
    rule = HoldemRule(schema_version="0.2", game_id="holdem", title="德州",
        deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},
        players={"min_players":2,"max_players":3,"starting_hand_size":2}, max_rounds=1, kind="holdem")
    plan = plan_for_rules(rule)
    assert {x["name"] for x in plan["tools"]} >= {"deck", "zones", "betting_round", "phase_progress", "community_deal", "all_in", "showdown", "settle_pots", "hand_rank"}
    assert len(plan["actions"]) == 5
