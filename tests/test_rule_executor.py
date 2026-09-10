from pocker_agent.game_layer import GameLayer
from pocker_agent.tools.plan import ToolPlan

def test_declared_actions_execute_and_record_state():
    plan = ToolPlan.model_validate({"game_kind":"test", "players":2,
      "tools":[{"name":"condition"}],
      "actions":[{"tool":"condition","operation":"call","args":{"condition":"hand_empty","hand_size":0},"result_key":"done"}]})
    result = GameLayer.from_plan(plan).execute()
    assert result["state"]["done"] is True
    assert result["events"][0]["tool"] == "condition"

def test_deal_result_can_feed_zone_action_without_code_execution():
    plan = ToolPlan.model_validate({"game_kind":"deal", "players":2,
      "tools":[{"name":"deck", "config":{"ranks":["A","K"],"suits":["S","H"]}}, {"name":"zones"}],
      "actions":[
        {"tool":"deck","operation":"deal","args":{"seed":3,"hands":2,"cards_each":1},"result_key":"deal"},
        {"tool":"zones","operation":"create","args":{"name":"hand-1","cards":"$state.deal.hands.0"},"result_key":"zone"}
      ]})
    result = GameLayer.from_plan(plan).execute()
    assert len(result["state"]["deal"]["hands"][0]) == 1
    assert result["state"]["zone"] == "hand-1"

def test_shedding_plan_deals_into_public_zones():
    from pocker_agent.game_rules import SheddingRule
    from pocker_agent.tools.plans import plan_for_rules
    rule = SheddingRule(schema_version="0.2", game_id="s", title="接牌",
        deck={"suits":["S","H","D","C"],"ranks":["A","2","3","4","5","6","7","8","9","10","J","Q","K"]},
        players={"min_players":2,"max_players":2,"starting_hand_size":5}, max_rounds=1,
        kind="shedding", match="suit_or_rank", wild_rank=None,
        draw_policy="until_playable", recycle_discard=True, blocked_result="draw")
    result = GameLayer.from_plan(ToolPlan.model_validate(plan_for_rules(rule))).execute()
    assert len(result["state"]["deal"]["hands"]) == 2
    zones = result["tool_state"]["zones"]["zones"]
    assert len(zones["stock"]) == 41 and len(zones["table"]) == 1
