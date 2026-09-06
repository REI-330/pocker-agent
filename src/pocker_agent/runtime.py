from __future__ import annotations

import json
import secrets
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

from .engine import RuleEngine
from .models import GameRuleDSL
from .storage import connect


@dataclass
class RuntimeSession:
    id: str
    engine: RuleEngine
    revision: int = 0
    seed: int = 0


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
        self.lock = threading.RLock()
        if path:
            with connect(path) as db:
                db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def _save(self, session):
        if self.path:
            with connect(self.path) as db:
                db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?)", (session.id, json.dumps(
                    {"engine": session.engine.serialize(), "revision": session.revision, "seed": session.seed})))
        else:
            self.sessions[session.id] = session

    def create(self, rules: GameRuleDSL, seed: int | None = None):
        seed = secrets.randbelow(2**31) if seed is None else seed
        session = RuntimeSession(uuid.uuid4().hex, RuleEngine(rules, seed=seed), seed=seed)
        session.engine.setup()
        run_bots(session.engine)
        with self.lock:
            self._save(session)
        return session

    def get(self, session_id):
        if self.path:
            with connect(self.path) as db:
                row = db.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row:
                data = json.loads(row[0])
                return RuntimeSession(session_id, RuleEngine.restore(data["engine"]), data["revision"], data["seed"])
        elif session_id in self.sessions:
            return self.sessions[session_id]
        raise KeyError("runtime_session_not_found")

    def act(self, session_id, action, revision, card_index=0):
        with self.lock:
            session = self.get(session_id)
            if session.revision != revision:
                raise ValueError("stale_revision: 牌局已经更新，请刷新牌局")
            start = len(session.engine.events)
            event = session.engine.step(action, card_index)
            run_bots(session.engine)
            session.revision += 1
            self._save(session)
            return {"event": event, "events": session.engine.events[start:], "state": snapshot(session)}


def snapshot(session):
    state = session.engine.state
    return {
        "session_id": session.id, "revision": session.revision, "seed": session.seed,
        "phase": state.phase, "round": state.round_number, "max_rounds": session.engine.rules.max_rounds,
        "current_player": state.players[state.current_player].id, "human_player": "player-1",
        "finished": state.finished, "winners": state.winners, "finish_reason": state.finish_reason,
        "legal_actions": session.engine.legal_actions(),
        "players": [{"id": p.id, "hand": [c.as_dict() for c in p.hand], "score": p.score} for p in state.players],
        "table": [c.as_dict() for c in state.table], "deck_remaining": len(state.deck),
        "events": session.engine.events[-100:],
    }


def export_package(rules):
    from .exporting import export_package as compile_export
    return compile_export(rules)
