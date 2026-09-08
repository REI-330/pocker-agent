import copy
import json

import pytest

from pocker_agent.agent import AgentSession, RuleAgent
from pocker_agent.build_jobs import BuildJobs
from pocker_agent.executors import create_engine, restore_engine
from pocker_agent.model_json import parse_object
from pocker_agent.plugin_builder import validate_scenarios
from pocker_agent.plugin_sandbox import execute, validate_frame
from pocker_agent.plugin_schema import PluginPlan, PluginRule
from pocker_agent.runtime import RuntimeSession, RuntimeStore, snapshot

# Test-only program exercising the universal protocol, not a production game template.
SOURCE = """(() => {
function setup(deck, n) {
 return {hands:[deck.filter((_,i)=>i%2===0),deck.filter((_,i)=>i%2===1)],deck:[],discard:[],
 current_player:0,finished:false,winners:[],scores:[0,0],phase:'移除一张',data:{}};
}
function actions(s) {
 if(s.finished) return [];
 let target=s.hands[s.current_player].length ? s.current_player : 1-s.current_player;
 return [{id:'remove',label:'移除一张',target_player:target,card_index:0}];
}
function step(s,a) {
 s.discard.push(s.hands[a.target_player].shift());
 if(s.hands.every(h=>h.length===0)) {s.finished=true;s.winners=[s.current_player];s.scores[s.current_player]=1;}
 else s.current_player=1-s.current_player;
 return s;
}
return {setup,actions,step};
})()"""


def state(hands, current=0):
    return dict(
        hands=hands,
        deck=[],
        discard=[],
        current_player=current,
        finished=False,
        winners=[],
        scores=[0, 0],
        phase="移除一张",
        data={},
    )


def plan():
    return dict(
        game_id="fixture",
        title="协议测试",
        deck={"suits": ["S", "H"], "ranks": ["A", "2"]},
        players={"min_players": 2, "max_players": 2, "starting_hand_size": 0},
        requirements=["轮流移除一张牌", "牌进入弃牌堆", "移除最后一张者胜"],
        scenarios=[
            {
                "name": "移动",
                "state": state([["AS"], ["AH"]]),
                "action_id": "remove",
                "expected": {"discard": ["AS"], "current_player": 1},
            },
            {
                "name": "空手继续",
                "state": state([[], ["AH", "2H"]]),
                "action_id": "remove",
                "expected": {"hands": [[], ["2H"]]},
            },
            {
                "name": "终局",
                "state": state([[], ["AH"]], 1),
                "action_id": "remove",
                "expected": {"finished": True, "winners": [1]},
            },
        ],
    )


def rule(source=SOURCE):
    return PluginRule(**plan(), source=source)


def test_generated_program_executes_and_restores_through_runtime(local_app):
    _, client, _ = local_app
    body = rule().model_dump(mode="json")
    assert (
        client.post("/api/agent/confirm", json={"proposal": body}).json()["kind"]
        == "confirmed"
    )
    response = client.post("/api/runtime/sessions?seed=7", json=body)
    assert response.status_code == 200
    initial = response.json()
    assert initial["kind"] == "plugin" and "seed" not in initial
    assert (
        not initial["players"][1]["hand"] and initial["players"][1]["hidden_count"] == 2
    )
    assert (
        "program_state" not in initial
        and initial["plugin_actions"][0]["id"] == "choice_0"
    )
    sid = initial["session_id"]
    bad = client.post(
        f"/api/runtime/sessions/{sid}/actions/invalid", json={"revision": 0}
    )
    assert bad.status_code == 422
    assert client.get(f"/api/runtime/sessions/{sid}").json() == initial
    for revision in (0, 1):
        result = client.post(
            f"/api/runtime/sessions/{sid}/actions/choice_0", json={"revision": revision}
        )
        assert result.status_code == 200
    final = result.json()["state"]
    assert final["finished"] and final["players"][1]["score"] == 1
    assert client.post("/api/simulations", json=body).json()["completed"]
    assert client.post("/api/games/export", json=body).status_code == 422


def test_unverified_but_well_formed_code_cannot_be_started(local_app):
    _, client, _ = local_app
    broken = rule(
        SOURCE.replace(
            "s.discard.push(s.hands[a.target_player].shift());",
            "s.hands[a.target_player].shift();",
        )
    )
    response = client.post("/api/runtime/sessions", json=broken.model_dump(mode="json"))
    assert response.status_code == 422 and "conservation" in response.json()["detail"]


@pytest.mark.parametrize(
    "expression",
    [
        "(()=>{while(true){} })()",
        "require('fs')",
        "fetch('https://example.com')",
        "process.env",
        "Math.random()",
    ],
)
def test_vm_limits_and_no_host_capabilities(expression):
    source = "({setup:()=> {return " + expression + ";}})"
    with pytest.raises(ValueError, match="plugin_"):
        execute(rule(source), "setup", deck=["AS"], players=2)


def test_vm_memory_exhaustion_is_a_visible_failure():
    source = (
        "({setup:()=> {const a=[];while(true)a.push(new Array(100000).fill('x'));}})"
    )
    with pytest.raises(ValueError, match="plugin_"):
        execute(rule(source), "setup", deck=["AS"], players=2)


def test_frame_rejects_duplicates_and_bad_hidden_card_positions():
    frame = {
        "state": state([["AS", "AS"], ["AH", "2H"]]),
        "actions": [{"id": "a", "label": "x"}],
    }
    with pytest.raises(ValueError, match="conservation"):
        validate_frame(rule(), frame)
    frame["state"] = state([["AS", "2S"], ["AH", "2H"]])
    frame["actions"][0].update(target_player=1, card_index=2)
    with pytest.raises(ValueError, match="position"):
        validate_frame(rule(), frame)


def test_model_repairs_source_against_unchanged_behavior_tests():
    broken = SOURCE.replace(
        "s.current_player=1-s.current_player", "s.current_player=s.current_player"
    )

    class Model:
        def __init__(self):
            self.responses = iter(
                [
                    {"type": "code"},
                    {"type": "plan", "plan": plan()},
                    {"source": broken},
                    {"source": SOURCE},
                ]
            )
            self.calls = []

        def complete(self, messages, **kwargs):
            self.calls.append(copy.deepcopy(messages))
            return json.dumps(next(self.responses))

    model = Model()
    result = RuleAgent(model).turn(AgentSession(), "生成一个轮流移除牌的游戏")
    assert result.kind == "proposal" and result.rules.kind == "plugin"
    assert [attempt["status"] for attempt in result.build] == ["failed", "passed"]
    assert result.rules.scenarios == PluginPlan(**plan()).scenarios
    assert "测试失败" in model.calls[-1][-1]["content"]


def test_program_state_restoration_has_no_aliases():
    engine = create_engine(rule(), 7)
    engine.setup()
    restored = restore_engine(engine.serialize())
    restored.extra["program_state"]["hands"][0].clear()
    assert engine.extra["program_state"]["hands"][0]


def test_plugin_source_and_progress_survive_new_sqlite_store(tmp_path):
    path = tmp_path / "games.db"
    first = RuntimeStore(path)
    session = first.create(rule(), seed=7)
    progressed = first.act(session.id, "choice_0", revision=0)["state"]
    restarted = RuntimeStore(path)
    loaded = restarted.get(session.id)
    assert loaded.engine.rules.source == SOURCE
    assert snapshot(loaded) == progressed
    final = restarted.act(session.id, "choice_0", revision=1)["state"]
    assert final["finished"] and final["revision"] == 2


def test_build_job_reports_progress_and_rejects_concurrent_build():
    import threading

    entered, release = threading.Event(), threading.Event()
    jobs = BuildJobs()

    def operation(progress):
        progress("编写代码")
        entered.set()
        assert release.wait(3)
        return {"kind": "proposal"}

    try:
        job = jobs.start(operation)
        assert entered.wait(3)
        assert jobs.get(job["id"])["progress"][0]["message"] == "编写代码"
        with pytest.raises(ValueError, match="已有游戏"):
            jobs.start(operation)
    finally:
        release.set()
        jobs.pool.shutdown(wait=True)
    assert jobs.get(job["id"])["status"] == "completed"
    with pytest.raises(ValueError, match="已失效"):
        jobs.get("missing")


def test_build_job_model_failure_is_visible():
    jobs = BuildJobs()

    def fail(progress):
        raise RuntimeError("upstream unavailable")

    job = jobs.start(fail)
    jobs.pool.shutdown(wait=True)
    assert jobs.get(job["id"])["status"] == "failed"
    assert jobs.get(job["id"])["error"] == "upstream unavailable"


@pytest.mark.parametrize("raw", ["plain text", "[]", "null", '{"ok":true} trailing'])
def test_gateway_without_json_mode_still_requires_valid_json(raw):
    with pytest.raises(RuntimeError):
        parse_object(raw)


def test_hidden_target_labels_and_internal_ids_are_not_forwarded():
    engine = create_engine(rule(), 7)
    engine.setup()
    engine.extra["program_actions"] = [
        {"id": "secret_AS", "label": "AS", "target_player": 1, "card_index": 0}
    ]

    public = snapshot(RuntimeSession("test", engine))
    assert public["plugin_actions"] == [
        {
            "id": "choice_0",
            "label": "从玩家2抽第1张牌",
            "target_player": 1,
            "card_index": 0,
        }
    ]


def test_excluded_cards_and_invalid_paths_rejected_before_coding():
    body = plan()
    body["excluded_cards"] = ["AS"]
    with pytest.raises(ValueError, match="被排除"):
        validate_scenarios(PluginPlan(**body))
    body = plan()
    body["scenarios"][0]["expected"] = {"hands[0]": []}
    with pytest.raises(ValueError):
        validate_scenarios(PluginPlan(**body))
    body = plan()
    body["scenarios"][0]["expected"] = {"hands.0": ["AS"], "discard": ["AS"]}
    with pytest.raises(ValueError, match="重复同一张牌"):
        validate_scenarios(PluginPlan(**body))


def test_fixture_action_ids_and_source_share_the_same_contract():
    colon_source = SOURCE.replace("id:'remove'", "id:'remove:p0'")
    body = plan()
    for scenario in body["scenarios"]:
        scenario["action_id"] = "remove:p0"
    from pocker_agent.plugin_sandbox import verify_plugin

    assert len(verify_plugin(PluginRule(**body, source=colon_source))) == 6


def test_inconsistent_plan_is_repaired_before_any_source_request():
    bad = plan()
    bad["scenarios"][0]["expected"] = {"hands.0": ["AS"], "discard": ["AS"]}

    class Model:
        def __init__(self):
            self.responses = iter([{"plan": bad}, {"plan": plan()}, {"source": SOURCE}])
            self.calls = []

        def complete(self, messages, **kwargs):
            self.calls.append(copy.deepcopy(messages))
            return json.dumps(next(self.responses))

    model = Model()
    result = RuleAgent(model).turn(AgentSession(), "请使用代码生成轮流移除牌游戏")
    assert result.kind == "proposal" and len(model.calls) == 3
    assert "先修正规则合约和测试" in model.calls[1][-1]["content"]
    assert result.rules.scenarios == PluginPlan(**plan()).scenarios


def test_existing_plugin_can_route_to_another_game():
    class Model:
        def complete(self, messages, **kwargs):
            return json.dumps({"type": "question", "question": "24点要出几题？"})

    session = AgentSession(proposal=rule().model_dump(mode="json"))
    result = RuleAgent(Model()).turn(session, "不要使用代码生成，改玩24点")
    assert result.kind == "question" and "24点" in result.message


def test_metadata_update_reuses_source_but_reruns_validation():
    from pocker_agent.plugin_builder import build_program

    updated = plan()
    updated["description"] = "修正后的准确说明"

    class Model:
        def complete(self, messages, **kwargs):
            return json.dumps({"type": "plan", "reuse_source": True, "plan": updated})

    result, attempts = build_program(
        Model(),
        [{"role": "user", "content": "只改说明，保持代码和测试"}],
        rule().model_dump(mode="json"),
    )
    assert result["rules"].source == SOURCE
    assert result["rules"].description == updated["description"]
    assert attempts[0]["reused_source"] is True and len(attempts[0]["checks"]) == 6
    report = attempts[0]["verification"]
    assert report["scenario"]["status"] == "passed"
    assert report["properties"]["status"] == "passed"
    assert report["independent_oracle"]["status"] == "not_available"


def test_metadata_reuse_cannot_change_executable_contract():
    from pocker_agent.plugin_builder import build_program

    updated = plan()
    updated["scenarios"][0]["expected"]["current_player"] = 0

    class Model:
        def complete(self, messages, **kwargs):
            return json.dumps({"type": "plan", "reuse_source": True, "plan": updated})

    with pytest.raises(ValueError, match="复用源码时只能修改说明"):
        build_program(Model(), [], rule().model_dump(mode="json"))
