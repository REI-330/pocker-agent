"""Host validation and subprocess lifecycle for generated JavaScript."""

import json
import os
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

from .plugin_schema import PluginAction, PluginState, card_catalog


def execute(rule, mode, **payload):
    request = {
        "source": rule.source,
        "catalog": card_catalog(rule),
        "mode": mode,
        **payload,
    }
    # -I ignores Python env/site customizations. The child gets no API secrets;
    # quickjs has no host callbacks or module loader and never runs shell code.
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    try:
        process = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).with_name("plugin_worker.py"))],
            input=json.dumps(request, ensure_ascii=True),
            capture_output=True,
            text=True,
            check=False,
            timeout=12 if mode == "simulate" else 3,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError("plugin_timeout: 生成代码运行超时，已终止") from error
    if process.returncode:
        raise ValueError("plugin_worker_failed: 隔离执行进程异常退出")
    if len(process.stdout) > 4_000_000:
        raise ValueError("plugin_output_limit")
    try:
        response = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("plugin_worker_invalid_response") from error
    if "error" in response:
        raise ValueError("plugin_execution_failed: " + response["error"])
    return response["result"]


def shuffled_deck(rule, seed):
    deck = list(card_catalog(rule))
    random.Random(seed).shuffle(deck)
    return deck


def validate_frame(rule, frame, expected_cards=None):
    state = PluginState.model_validate(frame["state"])
    count = rule.players.min_players
    if (
        len(state.hands) != count
        or len(state.scores) != count
        or state.current_player >= count
    ):
        raise ValueError("plugin_invalid_player_state")
    cards = state.deck + state.discard + [c for hand in state.hands for c in hand]
    expected = list(card_catalog(rule)) if expected_cards is None else expected_cards
    if len(expected) != len(set(expected)):
        raise ValueError("plugin_fixture_duplicate_cards")
    if Counter(cards) != Counter(expected):
        raise ValueError("plugin_card_conservation: cards lost, duplicated or invented")
    if not set(cards) <= card_catalog(rule).keys():
        raise ValueError("plugin_unknown_card")
    if len(set(state.winners)) != len(state.winners) or any(
        p < 0 or p >= count for p in state.winners
    ):
        raise ValueError("plugin_invalid_winners")
    if state.finished != bool(state.winners):
        raise ValueError("plugin_finish_requires_winners_and_active_requires_none")
    raw_actions = frame["actions"]
    if not isinstance(raw_actions, list) or len(raw_actions) > 256:
        raise ValueError("plugin_action_limit")
    actions = [PluginAction.model_validate(a) for a in raw_actions]
    if len({a.id for a in actions}) != len(actions):
        raise ValueError("plugin_duplicate_action_id")
    if state.finished == bool(actions):
        raise ValueError("plugin_finished_has_actions_or_active_deadlock")
    for action in actions:
        if action.target_player is not None:
            if (
                action.target_player >= count
                or action.card_index is None
                or action.card_index >= len(state.hands[action.target_player])
            ):
                raise ValueError("plugin_invalid_target_position")
    return state, actions


def simulate_plugin(rule, seed=7):
    trace = execute(
        rule,
        "simulate",
        deck=shuffled_deck(rule, seed),
        players=rule.players.min_players,
        seed=seed,
        max_steps=rule.max_steps,
    )
    for frame in trace:
        validate_frame(rule, frame)
    return trace


def verify_plugin(rule, progress=lambda message: None):
    """Backward-compatible check list; use ``verify_plugin_report`` for UI/statuses."""
    return verify_plugin_report(rule, progress)["checks"]


def verify_plugin_report(rule, progress=lambda message: None):
    """Run independent structural/property checks and keep their status separate.

    The model-authored scenarios are intentionally reported separately from the
    host-owned properties.  Passing a scenario is not presented as proof that
    the natural-language rule is semantically correct.
    """
    checks = []
    scenario_checks = []
    for scenario in rule.scenarios:
        progress("验证规则案例：" + scenario.name)
        state = scenario.state.model_dump(mode="json")
        cards = (
            state["deck"]
            + state["discard"]
            + [c for hand in state["hands"] for c in hand]
        )
        before = {"state": state, "actions": execute(rule, "actions", state=state)}
        validate_frame(rule, before, cards)
        legal_ids = [a["id"] for a in before["actions"]]
        if scenario.action_id not in legal_ids:
            raise ValueError(
                f"scenario {scenario.name}: required action_id {scenario.action_id!r}, but actions returned {legal_ids!r}; implement the fixed action IDs"
            )
        frame = execute(rule, "step", state=state, action_id=scenario.action_id)
        validate_frame(rule, frame, cards)
        for path, expected in scenario.expected.items():
            actual = frame["state"]
            for part in path.split("."):
                actual = actual[int(part)] if isinstance(actual, list) else actual[part]
            if actual != expected:
                raise ValueError(
                    f"scenario {scenario.name}: {path} expected {expected!r}, received {actual!r}"
                )
        scenario_checks.append(scenario.name)
        checks.append(scenario.name)
    property_checks = []
    for seed in (0, 7, 23):
        progress(f"模拟整局并检查牌张守恒：种子 {seed}")
        trace = simulate_plugin(rule, seed)
        if trace != simulate_plugin(rule, seed):
            raise ValueError(
                "plugin_nondeterministic: identical inputs produce different games"
            )
        checks.append(f"seed-{seed}: {len(trace) - 1} moves, deterministic, completed")
        property_checks.append(f"seed-{seed}: deterministic, completed")
        # Re-run every emitted action from the prior frame. This is independent
        # of the model's expected fields and catches a non-replayable transition.
        for before_frame, after_frame in zip(trace, trace[1:]):
            _, actions = validate_frame(rule, before_frame)
            action_ids = {a.id for a in actions}
            emitted = after_frame.get("action")
            if emitted is not None and emitted.get("id") not in action_ids:
                raise ValueError("plugin_replay_action_not_legal")
    return {
        "checks": checks,
        "scenario": {"status": "passed", "cases": scenario_checks},
        "properties": {"status": "passed", "checks": property_checks},
        "independent_oracle": {"status": "not_available", "message": "该 game_id 尚无人工 oracle，不能声称语义已证明"},
        "browser": {"status": "not_run", "message": "需要人工浏览器整局验收"},
    }
