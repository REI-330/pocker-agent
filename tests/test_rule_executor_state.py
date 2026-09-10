from pocker_agent.game_layer import GameLayer
from pocker_agent.tools.plan import ToolPlan

def test_tool_state_reference_moves_dealt_card_between_zones():
    plan = ToolPlan.model_validate({"game_kind":"state", "players":2,
      "tools":[{"name":"deck", "config":{"ranks":["A","K"],"suits":["S","H"]}}, {"name":"zones"}],
      "actions":[
        {"tool":"deck","operation":"deal","args":{"seed":1,"hands":2,"cards_each":1},"result_key":"deal"},
        {"tool":"zones","operation":"create","args":{"name":"hand","cards":"$state.deal.hands.0"}},
        {"tool":"zones","operation":"create","args":{"name":"table"}},
        {"tool":"zones","operation":"move","args":{"source":"hand","target":"table","cards":["$tool.zones.zones.hand.0"]}}
      ]})
    result = GameLayer.from_plan(plan).execute()
    assert result["tool_state"]["zones"]["zones"]["hand"] == []
    assert len(result["tool_state"]["zones"]["zones"]["table"]) == 1
