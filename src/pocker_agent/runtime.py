from __future__ import annotations

import json
import hashlib
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .engine import RuleEngine
from .executors import create_engine, restore_engine
from .family_engines import FamilyEngine
from .game_rules import PlayableRule
from .storage import connect
from .tools.plan import ToolPlan
from .tools.plans import plan_for_rules
from .game_layer import GameLayer


@dataclass
class ToolPlanRuntime:
    """Deterministic host boundary for an Agent-generated :class:`ToolPlan`.

    The Agent only supplies a declarative plan.  This object owns plan
    validation, tool allow-list enforcement and the lifecycle around a
    deterministic game executor.  Family engines remain injectable during the
    migration, but they can no longer silently emit an undeclared tool call.
    """

    plan: dict[str, Any]
    layer: GameLayer = field(init=False)
    composition: dict[str, Any] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        validated = ToolPlan.model_validate(self.plan)
        self.plan = validated.model_dump(mode="json")
        self.layer = GameLayer.from_plan(validated)

    @property
    def declared_tools(self) -> set[str]:
        return {item["name"] for item in self.plan.get("tools", [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)}

    def compose(self) -> dict[str, Any]:
        """Execute the declarative setup actions exactly once."""
        if self.composition is None:
            self.composition = self.layer.execute()
        return self.composition

    def execute_actions(self, actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Execute declarative ToolPlan actions through the generic interpreter.

        This is the runtime entry point for games that do not need a family
        executor: every action is resolved against the shared ToolContext and
        only declared operations can run.
        """
        from .rule_executor import RuleExecutor
        if actions is not None:
            original = self.layer.plan.get("actions", [])
            self.layer.plan["actions"] = actions
            try:
                return RuleExecutor(self.layer).run()
            finally:
                self.layer.plan["actions"] = original
        return RuleExecutor(self.layer).run()

    def create_executor(self, rules, *, seed: int, player_count: int | None = None):
        """Create the current host executor behind the ToolPlan boundary.

        Keeping construction here makes the migration seam explicit: new
        generic plans can replace this factory without changing the API or
        persistence lifecycle.
        """
        return create_engine(rules, seed=seed, player_count=player_count, tool_plan=self.plan)

    def validate_events(self, events: list[dict[str, Any]]) -> None:
        """Reject host execution that calls tools absent from the plan."""
        declared = self.declared_tools
        for event in events:
            if event.get("event") != "tool_called":
                continue
            tool = event.get("tool")
            if tool not in declared:
                raise ValueError(f"tool_not_declared:{tool}")

    def start(self, engine: Any) -> list[dict[str, Any]]:
        before = len(getattr(engine, "events", []))
        result = engine.setup()
        self.validate_events(getattr(engine, "events", [])[before:])
        return result

    def turn(self, engine: Any, operation: Callable[[], Any]) -> Any:
        """Run one deterministic host operation and commit only valid events."""
        before = len(getattr(engine, "events", []))
        result = operation()
        self.validate_events(getattr(engine, "events", [])[before:])
        return result


@dataclass
class RuntimeSession:
    id: str
    engine: RuleEngine | FamilyEngine
    revision: int = 0
    seed: int = 0
    tool_plan: dict | None = None
    composition: dict | None = None
    tool_runtime: ToolPlanRuntime | None = None
    tool_plan_source: str = "host_fallback"


def run_bots(engine):
    for _ in range(10000):
        if engine.state.finished or engine.state.current_player == 0:
            return
        engine.step()
    raise RuntimeError("bot_step_limit: 电脑回合超过上限，请简化规则")


class RuntimeStore:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.sessions = {}
        self.generated_plans = {}
        self.lock = threading.RLock()
        if path:
            with connect(path) as db:
                db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS generated_plans (digest TEXT PRIMARY KEY, source TEXT NOT NULL)")

    @staticmethod
    def plan_digest(rules, plan):
        canonical = {"rules": rules.model_dump(mode="json"),
                     "plan": ToolPlan.model_validate(plan).model_dump(mode="json")}
        return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def register_generated_plan(self, rules, plan, source):
        """Called by the server after model generation, never from client metadata."""
        digest = self.plan_digest(rules, plan)
        if self.path:
            with connect(self.path) as db:
                db.execute("INSERT OR REPLACE INTO generated_plans VALUES (?, ?)", (digest, source))
        else:
            self.generated_plans[digest] = source

    def plan_source(self, rules, plan):
        if plan is None:
            return "host_fallback"
        digest = self.plan_digest(rules, plan)
        if self.path:
            with connect(self.path) as db:
                row = db.execute("SELECT source FROM generated_plans WHERE digest=?", (digest,)).fetchone()
            return row[0] if row else "provided_plan"
        return self.generated_plans.get(digest, "provided_plan")

    def _save(self, session):
        if self.path:
            with connect(self.path) as db:
                db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?)", (session.id, json.dumps(
                    {"engine": session.engine.serialize(), "revision": session.revision, "seed": session.seed,
                     "tool_plan": session.tool_plan, "tool_plan_source": session.tool_plan_source, "composition": session.composition})))
        else:
            self.sessions[session.id] = session

    def create(self, rules: PlayableRule, seed: int | None = None, player_count: int | None = None, tool_plan: dict | None = None):
        seed = secrets.randbelow(2**31) if seed is None else seed
        source = self.plan_source(rules, tool_plan)
        plan = tool_plan or plan_for_rules(rules)
        tool_runtime = ToolPlanRuntime(plan)
        plan = tool_runtime.plan
        if plan["game_kind"] != getattr(rules, "kind", "legacy"):
            raise ValueError("tool_plan_game_kind_mismatch")
        if not rules.players.min_players <= plan["players"] <= rules.players.max_players:
            raise ValueError("tool_plan_player_count_mismatch")
        composition = tool_runtime.compose()
        session = RuntimeSession(uuid.uuid4().hex, tool_runtime.create_executor(rules, seed=seed, player_count=player_count), seed=seed,
                                 tool_plan=plan, composition=composition, tool_runtime=tool_runtime,
                                 tool_plan_source=source)
        tool_runtime.start(session.engine)
        run_bots(session.engine)
        tool_runtime.validate_events(session.engine.events)
        with self.lock:
            self._save(session)
        return session

    def get(self, session_id):
        if self.path:
            with connect(self.path) as db:
                row = db.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row:
                data = json.loads(row[0])
                engine = restore_engine(data["engine"])
                if hasattr(engine, "tool_plan"):
                    engine.tool_plan = data.get("tool_plan") or {}
                    engine._declared_tools = {item.get("name") for item in engine.tool_plan.get("tools", [])
                                              if isinstance(item, dict)}
                persisted_plan = data.get("tool_plan")
                tool_runtime = ToolPlanRuntime(persisted_plan or plan_for_rules(engine.rules))
                tool_runtime.composition = data.get("composition")
                source = self.plan_source(engine.rules, persisted_plan)
                if data.get("tool_plan_source") in {"host_fallback", "host_compatibility_compiler"}:
                    source = data["tool_plan_source"]
                tool_runtime.validate_events(engine.events)
                return RuntimeSession(session_id, engine, data["revision"], data["seed"],
                                      tool_runtime.plan, tool_runtime.composition, tool_runtime,
                                      source)
        elif session_id in self.sessions:
            return self.sessions[session_id]
        raise KeyError("runtime_session_not_found")

    def act(self, session_id, action, revision, card_index=0, *, expression="", declared_suit="", amount=None):
        with self.lock:
            session = self.get(session_id)
            if session.revision != revision:
                raise ValueError("stale_revision: 牌局已经更新，请刷新牌局")
            # Execute on a copy; rejected actions must not mutate even an in-memory session.
            restored = restore_engine(session.engine.serialize())
            if hasattr(restored, "tool_plan"):
                restored.tool_plan = session.tool_plan or {}
                restored._declared_tools = {item.get("name") for item in restored.tool_plan.get("tools", [])
                                            if isinstance(item, dict)}
            tool_runtime = ToolPlanRuntime(session.tool_plan or plan_for_rules(restored.rules))
            tool_runtime.composition = session.composition
            session = RuntimeSession(session.id, restored, session.revision, session.seed,
                                     tool_runtime.plan, tool_runtime.composition, tool_runtime,
                                     session.tool_plan_source)
            start = len(session.engine.events)
            engine_kind = getattr(session.engine, "kind", None) or getattr(session.engine.rules, "kind", None)
            if engine_kind == "holdem":
                operation = lambda: session.engine.step(action, card_index, expression=expression, declared_suit=declared_suit, amount=amount)
            elif engine_kind in {"arithmetic", "blackjack", "shedding"}:
                operation = lambda: session.engine.step(action, card_index, expression=expression, declared_suit=declared_suit)
            elif getattr(session.engine, "execution_mode", None) == "tool_flow":
                operation = lambda: session.engine.step(action, card_index, expression=expression,
                                                        declared_suit=declared_suit, amount=amount)
            else:
                operation = lambda: session.engine.step(action, card_index)
            event = tool_runtime.turn(session.engine, operation)
            run_bots(session.engine)
            tool_runtime.validate_events(session.engine.events)
            session.revision += 1
            self._save(session)
            return {"event": event, "events": session.engine.events[start:], "state": snapshot(session)}


def snapshot(session):
    state = session.engine.state
    # Composition actions are compile-time validation.  Live tool_events are
    # sourced only from the running game so a setup preflight cannot masquerade
    # as a second deal in the actual hand.
    tool_events = [event for event in session.engine.events
                   if event.get("event") == "tool_called"]
    composition_events = list((session.composition or {}).get("events", []))
    if getattr(session.engine, "execution_mode", None) == "tool_flow":
        # The shuffle seed reconstructs hidden hands and later rounds.
        result = {"session_id": session.id, "revision": session.revision}
        result.update(session.engine.view())
        result["tool_plan"] = session.tool_plan
        result["tool_plan_source"] = session.tool_plan_source
        result["tool_events"] = tool_events
        result["composition_events"] = composition_events
        return result
    if getattr(session.engine, "kind", None) in {"doudizhu", "holdem"}:
        result = {"session_id": session.id, "revision": session.revision, "seed": session.seed}
        result.update(session.engine.view())
        result["tool_plan"] = session.tool_plan
        result["tool_plan_source"] = session.tool_plan_source
        result["tool_events"] = tool_events
        result["composition_events"] = composition_events
        return result
    result = {
        "session_id": session.id, "revision": session.revision, "seed": session.seed,
        "phase": state.phase, "round": state.round_number, "max_rounds": session.engine.rules.max_rounds,
        "current_player": state.players[state.current_player].id, "human_player": "player-1",
        "finished": state.finished, "winners": state.winners, "finish_reason": state.finish_reason,
        "legal_actions": session.engine.legal_actions(),
        "players": [{"id": p.id, "hand": [c.as_dict() for c in p.hand], "score": p.score} for p in state.players],
        "table": [c.as_dict() for c in state.table], "deck_remaining": len(state.deck),
        "events": session.engine.events[-100:],
    }
    if hasattr(session.engine, "view"):
        result.update(session.engine.view())
        if result.get("kind") in {"blackjack", "shedding", "plugin"} and not state.finished:
            # A seed would let a client reconstruct private hands and the remaining deck.
            result.pop("seed", None)
    result["tool_plan"] = session.tool_plan
    result["tool_plan_source"] = session.tool_plan_source
    result["tool_events"] = tool_events
    result["composition_events"] = composition_events
    return result


def export_package(rules):
    from .exporting import export_package as compile_export
    return compile_export(rules)
