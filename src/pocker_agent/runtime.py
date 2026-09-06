from __future__ import annotations

import io
import json
import uuid
import zipfile
from dataclasses import dataclass
from typing import Any

from .engine import RuleEngine
from .models import GameRuleDSL


@dataclass
class RuntimeSession:
    id: str
    engine: RuleEngine


class RuntimeStore:
    def __init__(self) -> None:
        self.sessions: dict[str, RuntimeSession] = {}

    def create(self, rules: GameRuleDSL, seed: int = 0) -> RuntimeSession:
        session = RuntimeSession(id=uuid.uuid4().hex, engine=RuleEngine(rules, seed=seed))
        session.engine.setup()
        self.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> RuntimeSession:
        try:
            return self.sessions[session_id]
        except KeyError as error:
            raise KeyError("runtime_session_not_found") from error


def snapshot(session: RuntimeSession) -> dict[str, Any]:
    state = session.engine.state
    return {
        "session_id": session.id,
        "phase": state.phase,
        "round": state.round_number,
        "current_player": state.players[state.current_player].id,
        "finished": state.finished,
        "legal_actions": session.engine.legal_actions() if not state.finished else [],
        "players": [{"id": player.id, "hand": [card.as_dict() for card in player.hand], "score": player.score} for player in state.players],
        "table": [card.as_dict() for card in state.table],
    }


def export_package(rules: GameRuleDSL) -> tuple[bytes, str]:
    manifest = {"name": rules.game_id, "version": rules.schema_version, "runtime": "pocker-agent-web-runtime-0.1", "rules": rules.model_dump(mode="json")}
    readme = f"# {rules.title}\n\nThis package contains a Pocker Agent DSL export. Load `game.json` with a compatible runtime.\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("game.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("README.md", readme)
    return buffer.getvalue(), f"{rules.game_id}.pocker-game.zip"
