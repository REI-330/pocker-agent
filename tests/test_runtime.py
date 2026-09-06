from pocker_agent.models import GameRuleDSL
from pocker_agent.runtime import RuntimeStore, export_package, snapshot
from zipfile import ZipFile
from io import BytesIO


def rules() -> GameRuleDSL:
    return GameRuleDSL.model_validate({
        "game_id": "runtime-demo", "title": "Runtime Demo",
        "deck": {"suits": ["S", "H"], "ranks": ["A", "K", "Q", "J"]},
        "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 1},
        "actions": [{"name": "play"}], "phases": [{"name": "main", "actions": ["play"]}],
    })


def test_runtime_session_exposes_legal_actions_and_updates_state():
    session = RuntimeStore().create(rules(), seed=2)
    before = snapshot(session)
    event = session.engine.step(before["legal_actions"][0])
    after = snapshot(session)
    assert event["event"] == "action_executed"
    assert after["current_player"] != before["current_player"]


def test_export_package_contains_dsl_manifest():
    content, filename = export_package(rules())
    assert filename == "runtime-demo.pocker-game.zip"
    with ZipFile(BytesIO(content)) as archive:
        assert "game.json" in archive.namelist()
        assert b"runtime-demo" in archive.read("game.json")
