import json

from pocker_agent.agent import AgentSession, RuleAgent


class FakeModel:
    def __init__(self, *responses: str):
        self.responses = list(responses)

    def complete(self, messages, *, response_format=None):
        return self.responses.pop(0)


class FailingRepairModel:
    def __init__(self, first_response: str):
        self.first_response = first_response
        self.calls = 0

    def complete(self, messages, *, response_format=None):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("upstream_timeout")
        return self.first_response


def valid_rules():
    return {
        "game_id": "agent-demo",
        "title": "Agent Demo",
        "deck": {"suits": ["S", "H"], "ranks": ["A", "K"]},
        "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 1},
        "actions": [{"name": "play"}],
        "phases": [{"name": "main", "actions": ["play"]}],
    }


def test_agent_asks_for_missing_rule_then_proposes():
    model = FakeModel(
        json.dumps({"type": "question", "question": "需要几名玩家？", "missing": ["player_count"]}),
        json.dumps({"type": "proposal", "summary": "规则已生成。", "rules": valid_rules()}),
    )
    agent = RuleAgent(model)
    session = AgentSession()
    first = agent.turn(session, "我想做一个比大小的游戏")
    second = agent.turn(session, "两名玩家，每人一张牌")
    assert first.kind == "question"
    assert second.kind == "proposal"
    assert second.rules is not None


def test_agent_repairs_invalid_dsl():
    broken = {**valid_rules(), "phases": [{"name": "main", "actions": ["missing"]}]}
    model = FakeModel(json.dumps({"type": "proposal", "rules": broken}), json.dumps(valid_rules()))
    result = RuleAgent(model).turn(AgentSession(), "生成规则")
    assert result.kind == "proposal"
    assert result.rules is not None


def test_confirm_requires_proposal():
    result = RuleAgent(FakeModel()).confirm(AgentSession())
    assert result.kind == "error"


def test_repair_failure_is_visible_to_caller():
    broken = {**valid_rules(), "phases": [{"name": "main", "actions": ["missing"]}]}
    model = FailingRepairModel(json.dumps({"type": "proposal", "rules": broken}))
    result = RuleAgent(model).turn(AgentSession(), "生成规则")
    assert result.kind == "error"
    assert any(error.startswith("repair_failed:") for error in result.errors)
