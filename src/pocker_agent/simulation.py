from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .executors import create_engine
from .tools.plans import plan_for_rules
from .game_rules import PlayableRule


@dataclass(frozen=True)
class SimulationResult:
    seed: int
    events: list[dict[str, Any]]
    winner: str | None
    completed: bool


def simulate(rules: PlayableRule, seed: int = 0, player_count: int | None = None, max_steps: int = 1000) -> SimulationResult:
    # Shedding's legacy simulator remains the compatibility path until its
    # draw-until-playable policy is represented as a declarative policy Tool.
    use_flow = getattr(rules, "kind", None) in {"arithmetic", "blackjack", "doudizhu", "holdem"}
    plan = plan_for_rules(rules) if use_flow else None
    engine = create_engine(rules, seed=seed, player_count=player_count, tool_plan=plan)
    if plan and plan.get("flow"):
        engine.setup()
        for _ in range(max_steps):
            if engine.state.finished:
                break
            actions = engine.legal_actions()
            action, payload = _simulation_action(rules, engine, actions)
            engine.step(action, **payload)
        events = engine.events
    else:
        events = engine.run(max_steps=max_steps)
    finish_events = [event for event in events if event["event"] == "game_finished"]
    return SimulationResult(
        seed=seed,
        events=events,
        winner=(finish_events[-1].get("winner") if finish_events and "winner" in finish_events[-1]
                else (finish_events[-1].get("winners") or [None])[0] if finish_events else None),
        completed=bool(finish_events),
    )


def _simulation_action(rules, engine, actions):
    """Choose a deterministic, explicit action for a tool-flow smoke run."""
    kind = getattr(rules, "kind", "")
    if "bid:*" in actions:
        values = next((t.get("config", {}).get("bidding_values", [0, 1, 2, 3])
                       for t in engine.tool_plan.get("tools", []) if t.get("name") == "doudizhu_turn"), [0, 1, 2, 3])
        return f"bid:{max(values)}", {}
    if "play:*" in actions:
        return "pass", {}
    if kind == "blackjack":
        return ("stand" if "stand" in actions else actions[0]), {}
    if kind == "arithmetic":
        return ("give_up" if "give_up" in actions else actions[0]), {}
    if kind == "shedding":
        return ("draw" if "draw" in actions else actions[0]), {}
    return (("check" if "check" in actions else "call" if "call" in actions else actions[0]), {})
