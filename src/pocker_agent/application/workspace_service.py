from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..agents.design import DesignAgent
from ..domain.rules import contract_review, parse_rule, rule_facts
from ..domain.workspace import Phase as ConversationPhase
from ..domain.workspace import Workspace
from ..infrastructure.storage import connect

ConversationStatus = ConversationPhase  # compatibility for early clients


@dataclass
class TurnResult:
    kind: str
    message: str
    rules: Any = None
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    proposal: dict[str, Any] | None = None
    confirmed: bool = False


@dataclass
class Conversation:
    id: str
    session: SessionState = field(default_factory=SessionState)
    phase: ConversationPhase = ConversationPhase.DESIGNING
    revision: int = 0
    request_id: str | None = None
    last_request_id: str | None = None
    last_result: dict[str, Any] | None = None
    job: dict[str, Any] | None = None
    error: str | None = None
    runtime_id: str | None = None
    draft: dict[str, str] | None = None
    facts: list[str] = field(default_factory=list)
    tool_plan: dict[str, Any] | None = None
    contract: dict[str, Any] | None = None

    @property
    def status(self):
        return self.phase

    def view(self):
        rule = parse_rule(self.session.proposal) if self.session.proposal else None
        return {
            "id": self.id,
            "conversation_id": self.id,
            "revision": self.revision,
            "phase": self.phase.value,
            "status": self.phase.value,
            "messages": self.session.messages,
            "draft": self.draft
            or ({"title": rule.title, "summary": rule.description} if rule else None),
            "proposal": self.session.proposal
            if self.phase
            in {
                ConversationPhase.PLAYABLE,
                ConversationPhase.BUILDING,
                ConversationPhase.PROPOSAL_READY,
                ConversationPhase.FAILED,
            }
            else None,
            "facts": self.facts or (rule_facts(rule) if rule else []),
            "contract": self.contract or (contract_review(rule) if rule else None),
            "tool_plan": self.tool_plan,
            "job": self.job,
            "error": self.error,
            "runtime_id": self.runtime_id,
        }


class ConversationService:
    def __init__(self, path=None):
        self.path = path
        self._items = {}
        self._lock = threading.RLock()
        if path:
            with connect(path) as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
                )

    def _save(self, item):
        if self.path:
            payload = {
                "messages": item.session.messages,
                "proposal": item.session.proposal,
                "confirmed": item.session.confirmed,
                "phase": item.phase.value,
                "revision": item.revision,
                "request_id": item.request_id,
                "last_request_id": item.last_request_id,
                "last_result": item.last_result,
                "job": item.job,
                "error": item.error,
                "runtime_id": item.runtime_id,
                "draft": item.draft,
                "facts": item.facts,
                "tool_plan": item.tool_plan,
                "contract": item.contract,
            }
            with connect(self.path) as db:
                db.execute(
                    "INSERT OR REPLACE INTO conversations VALUES (?,?)",
                    (item.id, json.dumps(payload, ensure_ascii=False)),
                )

    def create(self):
        with self._lock:
            item = Conversation(uuid.uuid4().hex)
            self._items[item.id] = item
            self._save(item)
            return item

    def get(self, cid):
        with self._lock:
            if cid in self._items:
                return self._items[cid]
            if self.path:
                with connect(self.path) as db:
                    row = db.execute(
                        "SELECT payload FROM conversations WHERE id=?", (cid,)
                    ).fetchone()
                if row:
                    d = json.loads(row[0])
                    item = Conversation(
                        id=cid,
                        session=SessionState(
                            d.get("messages", []),
                            d.get("proposal"),
                            d.get("confirmed", False),
                        ),
                        phase=ConversationPhase(d.get("phase", "designing")),
                        revision=d.get("revision", 0),
                        request_id=d.get("request_id"),
                        last_request_id=d.get("last_request_id"),
                        last_result=d.get("last_result"),
                        job=d.get("job"),
                        error=d.get("error"),
                        runtime_id=d.get("runtime_id"),
                        draft=d.get("draft"),
                        facts=d.get("facts", []),
                        tool_plan=d.get("tool_plan"),
                        contract=d.get("contract"),
                    )
                    if item.phase in {
                        ConversationPhase.THINKING,
                        ConversationPhase.BUILDING,
                    }:
                        item.phase = ConversationPhase.FAILED
                        item.error = "服务重启导致未完成的任务中断，请重试"
                    self._items[cid] = item
                    self._save(item)
                    return item
            raise KeyError("conversation_not_found")

    def turn(self, cid, text, model, request_id=None, revision=None):
        with self._lock:
            item = self.get(cid)
            token = request_id or uuid.uuid4().hex
            if item.last_request_id == token and item.last_result:
                return TurnResult(**item.last_result)
            if revision is not None and revision != item.revision:
                raise ValueError("stale_conversation_revision")
            if item.phase in {ConversationPhase.BUILDING, ConversationPhase.THINKING}:
                raise ValueError("conversation_busy")
            if not text.strip():
                raise ValueError("message_empty")
            # Persist the user turn before inference so the model receives the
            # exact message that triggered this request.
            item.session.messages.append({"role": "user", "content": text})
            # A design revision invalidates every executable artifact. Keeping
            # an old job here would let polling republish the previous game.
            item.session.proposal = None
            item.session.confirmed = False
            item.draft = None
            item.facts = []
            item.tool_plan = None
            item.contract = None
            item.runtime_id = None
            item.job = None
            item.phase = ConversationPhase.THINKING
            item.request_id = token
            item.error = None
            self._save(item)
            workspace = Workspace(
                id=item.id,
                revision=item.revision,
                messages=list(item.session.messages),
                draft=item.draft,
            )

        class Context:
            def check(self):
                return None

            def progress(self, _message):
                return None

            def on_cancel(self, _interrupt):
                return None

        try:
            # Model inference is deliberately outside the repository lock. A
            # cancel request can therefore release the UI immediately.
            message, draft = DesignAgent(lambda: model).reply(workspace, Context())
        except Exception as exc:
            with self._lock:
                item = self.get(cid)
                if item.request_id == token:
                    item.phase = ConversationPhase.FAILED
                    item.error = str(exc)
                    item.request_id = None
                    item.revision += 1
                    self._save(item)
            raise
        with self._lock:
            item = self.get(cid)
            if item.request_id != token or item.phase != ConversationPhase.THINKING:
                raise ValueError("conversation_cancelled")
            item.session.messages.append({"role": "assistant", "content": message})
            item.draft = draft.model_dump(mode="json") if draft else None
            result = TurnResult("proposal" if draft else "question", message)
            item.request_id = None
            item.last_request_id = token
            item.last_result = result.__dict__.copy()
            item.revision += 1
            item.phase = (
                ConversationPhase.PROPOSAL_READY
                if item.draft
                else ConversationPhase.DESIGNING
            )
            self._save(item)
            return result

    def confirm(self, cid, revision):
        with self._lock:
            item = self.get(cid)
            if revision != item.revision:
                raise ValueError("stale_conversation_revision")
            if (
                item.phase
                not in {ConversationPhase.PROPOSAL_READY, ConversationPhase.FAILED}
                or not item.draft
            ):
                return TurnResult(
                    "error", "还没有可以确认的规则。", errors=["proposal_missing"]
                )
            item.session.confirmed = True
            item.phase = ConversationPhase.BUILDING
            item.revision += 1
            self._save(item)
            return TurnResult("confirmed", "规则已确认，可以开始生成游戏。")

    def cancel(self, cid, revision):
        with self._lock:
            item = self.get(cid)
            if revision != item.revision:
                raise ValueError("stale_conversation_revision")
            item.request_id = None
            item.job = {**item.job, "status": "cancelled"} if item.job else None
            item.phase = (
                ConversationPhase.PROPOSAL_READY
                if item.draft
                else ConversationPhase.DESIGNING
            )
            item.error = None
            item.revision += 1
            self._save(item)
            return item

    def attach_job(self, cid, job):
        with self._lock:
            item = self.get(cid)
            item.job = job
            self._save(item)
            return item

    def set_runtime(self, cid, runtime_id):
        with self._lock:
            item = self.get(cid)
            item.runtime_id = runtime_id
            self._save(item)
            return item

    def fail(self, cid, message):
        with self._lock:
            item = self.get(cid)
            item.phase = ConversationPhase.FAILED
            item.error = message
            item.revision += 1
            self._save(item)
            return item

    def publish_build(self, cid, job):
        with self._lock:
            item = self.get(cid)
            if item.job and item.job.get("id") != job.get("id"):
                return item
            if item.job and item.job.get("status") == "cancelled":
                return item
            if (
                item.job
                and item.job.get("status") == job.get("status")
                and job.get("status") in {"completed", "failed", "cancelled"}
            ):
                return item
            if job.get("status") == "running":
                running = {
                    k: job.get(k) for k in ("id", "kind", "status", "progress", "error")
                }
                if item.job == running:
                    return item
                item.job = running
                item.revision += 1
                self._save(item)
                return item
            if job.get("status") == "completed" and job.get("result"):
                result = job["result"]
                item.session.proposal = result.get("rules")
                item.job = {
                    k: job.get(k) for k in ("id", "kind", "status", "progress", "error")
                }
                item.facts = result.get("facts", [])
                item.tool_plan = result.get("tool_plan")
                item.contract = result.get("contract")
                item.phase = (
                    ConversationPhase.PLAYABLE
                    if item.session.proposal
                    else ConversationPhase.FAILED
                )
                item.error = (
                    None
                    if item.phase == ConversationPhase.PLAYABLE
                    else result.get("message")
                )
            elif job.get("status") in {"failed", "cancelled"}:
                item.job = {
                    k: job.get(k) for k in ("id", "kind", "status", "progress", "error")
                }
                item.phase = (
                    ConversationPhase.FAILED
                    if job.get("status") == "failed"
                    else (
                        ConversationPhase.PROPOSAL_READY
                        if item.draft
                        else ConversationPhase.DESIGNING
                    )
                )
                item.error = job.get("error")
            item.revision += 1
            self._save(item)
            return item
