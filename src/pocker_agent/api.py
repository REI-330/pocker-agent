from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agents.generation import AgentSession, RuleAgent
from .configuration import ConfigInput, ConfigStore
from .llm import OpenAICompatibleClient
from .domain.rules import PlayableRule, contract_review, rule_facts, parse_rule
from .game_runtime.engines.factory import create_engine
from .game_runtime.sessions import RuntimeStore, ToolPlanRuntime, snapshot
from .game_runtime.exporting import export_package
from .game_runtime.simulation import simulate
from .infrastructure.storage import data_path
from .domain.validation import validate_dsl
from .build_jobs import BuildJobs
from .capabilities import capability_matrix
from .game_runtime.composition import GameLayer
from .game_runtime.tools import ToolPlan, default_registry, plan_for_rules
from .engine_agent import EngineAgent
from .application.workspace_service import ConversationService


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=40000)


class TurnInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    messages: list[Message] = Field(default_factory=list, max_length=60)
    proposal: dict | None = None
    request_id: str | None = Field(default=None, max_length=80)
    revision: int | None = Field(default=None, ge=0)


class ConfirmInput(BaseModel):
    proposal: dict | None = None
    messages: list[Message] = Field(default_factory=list)
    tool_plan: dict | None = None
    conversation_id: str | None = None
    revision: int | None = None


class ActionInput(BaseModel):
    revision: int = Field(ge=0)
    card_index: int = Field(default=0, ge=0)
    expression: str = Field(default="", max_length=256)
    declared_suit: str = Field(default="", max_length=16)
    amount: int | None = Field(default=None, ge=0)


class WorkspaceCommand(BaseModel):
    revision: int = Field(ge=0)
    seed: int | None = None


def create_app(path: Path | None = None, vault=None):
    app = FastAPI(title="Pocker Agent", version="0.2.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    path = path or data_path()
    config = ConfigStore(path, vault)
    runtime = RuntimeStore(path)
    builds = BuildJobs()
    conversations = ConversationService(path)
    app.state.conversations = conversations
    app.state.config_store = config
    app.state.runtime_store = runtime
    app.mount("/assets", StaticFiles(directory=Path(__file__).parent / "assets"), name="assets")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo request inputs: configuration bodies contain credentials.
        return JSONResponse(status_code=422, content={"detail": "; ".join(
            f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}" for issue in error.errors())})

    @app.exception_handler(ValueError)
    async def bad_value(request, error):
        return JSONResponse(status_code=409 if str(error).startswith("stale_revision") else 422, content={"detail": str(error)})

    @app.exception_handler(RuntimeError)
    async def operation_error(request, error):
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "本机数据库不可用，操作未完成"})

    @app.exception_handler(KeyError)
    async def not_found(request, error):
        return JSONResponse(status_code=404, content={"detail": "牌局不存在，请重新开始试玩"})

    def model_client():
        saved = config.read()
        if not saved.public()["configured"]:
            raise ValueError("请先保存模型配置")
        return OpenAICompatibleClient.from_config(saved)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0"}

    @app.get("/api/capabilities")
    def capabilities():
        result = capability_matrix()
        result["tools"] = default_registry().names()
        return result

    @app.get("/api/tools")
    def tools():
        return {"tools": default_registry().names(), "composition": "ToolPlan -> GameLayer"}

    @app.post("/api/tools/plan/validate")
    def validate_tool_plan(payload: dict):
        try:
            plan = ToolPlan.model_validate(payload)
            layer = GameLayer.from_plan(plan)
            return {"valid": True, "plan": plan.model_dump(mode="json"), "layer": layer.describe()}
        except ValueError as error:
            return {"valid": False, "errors": [str(error)]}

    @app.post("/api/tools/plan/execute")
    def execute_tool_plan(payload: dict):
        """Run declared actions only; no source code or dynamic imports accepted."""
        try:
            plan = ToolPlan.model_validate(payload)
            layer = GameLayer.from_plan(plan)
            return {"valid": True, "result": layer.execute()}
        except (ValueError, TypeError) as error:
            return {"valid": False, "errors": [str(error)]}

    @app.get("/api/agent/config")
    def get_config():
        return config.read().public()

    @app.post("/api/agent/config")
    def save_config(payload: ConfigInput):
        return config.save(payload)

    @app.post("/api/agent/models")
    def discover(payload: ConfigInput):
        draft = config.draft(payload, require_model=False)
        names = OpenAICompatibleClient.from_config(draft).list_models()
        return {"models": names, "base_url": draft.base_url}

    @app.post("/api/agent/test-connection")
    def test_connection(payload: ConfigInput):
        draft = config.draft(payload)
        result = OpenAICompatibleClient.from_config(draft).complete([{"role": "user", "content": "Reply with OK."}])
        return {"ok": bool(result), "model": draft.model, "base_url": draft.base_url}

    def generate(payload: TurnInput, client, progress=lambda message: None):
        if not payload.message.strip():
            raise ValueError("请输入玩法")
        session = AgentSession([m.model_dump() for m in payload.messages], payload.proposal)
        result = RuleAgent(client, progress).turn(session, payload.message)
        if result.rules is not None and result.tool_plan is not None:
            runtime.register_generated_plan(result.rules, result.tool_plan, result.tool_plan_source)
        return {"kind": result.kind, "message": result.message, "missing": result.missing,
                "errors": result.errors, "rules": result.rules.model_dump(mode="json") if result.rules else None,
                "messages": session.messages, "facts": rule_facts(result.rules) if result.rules else [],
                "contract": contract_review(result.rules) if result.rules else None, "build": result.build,
                "tool_plan": result.tool_plan if result.rules else None,
                "tool_plan_source": result.tool_plan_source if result.rules else None}

    @app.post("/api/agent/turn")
    def turn(payload: TurnInput):
        return generate(payload, model_client())

    @app.post("/api/conversations")
    def create_conversation():
        return conversations.create().view()

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: str):
        item = conversations.get(conversation_id)
        if item.job:
            try:
                job = builds.get(item.job.get("id"))
                item = conversations.publish_build(conversation_id, job)
            except ValueError as error:
                # A bounded in-memory job can expire independently of the
                # SQLite conversation. Surface that loss instead of leaving a
                # permanently polling `building` session.
                if item.phase.value == "building":
                    item = conversations.fail(conversation_id, str(error))
        return item.view()

    @app.post("/api/conversations/{conversation_id}/turn")
    def conversation_turn(conversation_id: str, payload: TurnInput):
        result = conversations.turn(conversation_id, payload.message, model_client(), payload.request_id, payload.revision)
        item = conversations.get(conversation_id)
        return {**item.view(), "kind": result.kind, "message": result.message, "missing": result.missing, "errors": result.errors}

    @app.post("/api/conversations/{conversation_id}/messages")
    def conversation_message(conversation_id: str, payload: TurnInput):
        return conversation_turn(conversation_id, payload)

    @app.post("/api/conversations/{conversation_id}/confirm")
    def conversation_confirm(conversation_id: str, payload: ConfirmInput):
        if payload.revision is None:
            raise ValueError("conversation_revision_required")
        result = conversations.confirm(conversation_id, payload.revision)
        item = conversations.get(conversation_id)
        if result.kind == "confirmed":
            try:
                client = model_client(); client.timeout_seconds = 600
                generation_payload = TurnInput(message="使用代码生成。以下规则已由用户确认，严格按此实现：\n" + item.draft["summary"], messages=[Message(**m) for m in item.session.messages], proposal=None)
                job = builds.start(lambda progress: generate(generation_payload, client, progress))
                conversations.attach_job(conversation_id, {"id": job["id"], "kind": "build", "status": "running", "progress": [], "error": None})
                item = conversations.get(conversation_id)
            except Exception as error:
                # Configuration, network, and queue failures all belong to
                # this transition; persist the visible failure before letting
                # FastAPI map the exception to its HTTP response.
                conversations.fail(conversation_id, str(error))
                raise
        return {**item.view(), "kind": result.kind, "message": result.message, "errors": result.errors}

    @app.post("/api/conversations/{conversation_id}/cancel")
    def conversation_cancel(conversation_id: str, payload: ConfirmInput):
        if payload.revision is None:
            raise ValueError("conversation_revision_required")
        item = conversations.get(conversation_id)
        if item.job and item.phase.value == "building":
            builds.cancel(item.job.get("id"))
        return conversations.cancel(conversation_id, payload.revision).view()

    @app.post("/api/conversations/{conversation_id}/build")
    def build_conversation(conversation_id: str):
        """Start code generation only after an explicit confirmation command."""
        item = conversations.get(conversation_id)
        if item.phase.value != "building": raise ValueError("conversation_must_be_confirmed_before_build")
        return builds.get(item.job["id"]) if item.job else {"id": None, "status": "running"}

    def confirmed_rules(conversation_id: str, revision: int):
        item = conversations.get(conversation_id)
        if revision != item.revision:
            raise ValueError("stale_conversation_revision")
        if item.phase.value != "playable" or not item.session.proposal:
            raise ValueError("conversation_game_not_ready")
        return item

    @app.post("/api/conversations/{conversation_id}/runtime")
    def conversation_runtime(conversation_id: str, payload: WorkspaceCommand):
        item = confirmed_rules(conversation_id, payload.revision)
        rules = parse_rule(item.session.proposal)
        state = snapshot(runtime.create(rules, payload.seed, tool_plan=item.tool_plan))
        conversations.set_runtime(conversation_id, state["session_id"])
        return state

    @app.post("/api/conversations/{conversation_id}/simulations")
    def conversation_simulation(conversation_id: str, payload: WorkspaceCommand):
        item = confirmed_rules(conversation_id, payload.revision)
        result = simulate(parse_rule(item.session.proposal), seed=payload.seed or 7)
        return {"completed": result.completed, "winner": result.winner, "events": result.events}

    @app.post("/api/conversations/{conversation_id}/export")
    def conversation_export(conversation_id: str, payload: WorkspaceCommand):
        item = confirmed_rules(conversation_id, payload.revision)
        content, filename = export_package(parse_rule(item.session.proposal))
        return Response(content, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @app.post("/api/agent/jobs")
    def start_build(payload: TurnInput):
        client = model_client()
        client.timeout_seconds = 7200
        return builds.start(lambda progress: generate(payload, client, progress))

    @app.get("/api/agent/jobs/{job_id}")
    def get_build(job_id: str):
        return builds.get(job_id)

    @app.post("/api/agent/confirm")
    def confirm(payload: ConfirmInput):
        # Confirmation and gameplay validate the contract; they need no model or key.
        if payload.proposal is None:
            raise ValueError("proposal_required")
        rules, errors = validate_dsl(payload.proposal)
        resolved_plan = payload.tool_plan or (plan_for_rules(rules) if rules else None)
        if rules and not errors and resolved_plan:
            try:
                checked = ToolPlan.model_validate(resolved_plan)
                if checked.game_kind != getattr(rules, "kind", "legacy"):
                    raise ValueError("tool_plan_game_kind_mismatch")
                missing = sorted(EngineAgent.required_tools(rules) - {item.name for item in checked.tools})
                if missing:
                    raise ValueError("tool_plan_missing_required:" + ",".join(missing))
                resolved_plan = checked.model_dump(mode="json")
                plan_runtime = ToolPlanRuntime(resolved_plan)
                plan_runtime.compose()
                engine = create_engine(rules, seed=7, tool_plan=resolved_plan)
                plan_runtime.start(engine)
                plan_runtime.validate_events(engine.events)
            except (ValueError, TypeError, RuntimeError) as error:
                errors.append(str(error))
        return {"kind": "error" if errors else "confirmed", "errors": errors,
                "rules": rules.model_dump(mode="json") if rules else None, "facts": rule_facts(rules) if rules else [],
                "contract": contract_review(rules) if rules else None,
                "tool_plan": resolved_plan,
                "tool_plan_source": runtime.plan_source(rules, payload.tool_plan) if rules else None}

    @app.post("/api/rules/validate")
    def validate(payload: dict):
        rules, errors = validate_dsl(payload)
        return {"valid": not errors, "errors": errors, "rules": rules.model_dump(mode="json") if rules else None}

    @app.post("/api/simulations")
    def simulation(rules: PlayableRule, seed: int = 7, player_count: int | None = None):
        result = simulate(rules, seed=seed, player_count=player_count)
        return {"completed": result.completed, "winner": result.winner, "events": result.events}

    @app.post("/api/runtime/sessions")
    def create_session(payload: dict, seed: int | None = None, player_count: int | None = None):
        raw_rules = payload.get("rules", payload)
        rules = parse_rule(raw_rules)
        return snapshot(runtime.create(rules, seed, player_count, payload.get("tool_plan")))

    @app.get("/api/runtime/sessions/{session_id}")
    def get_session(session_id: str):
        return snapshot(runtime.get(session_id))

    @app.post("/api/runtime/sessions/{session_id}/actions/{action}")
    def act(session_id: str, action: str, payload: ActionInput):
            return runtime.act(session_id, action, payload.revision, payload.card_index,
                               expression=payload.expression, declared_suit=payload.declared_suit,
                               amount=payload.amount)

    @app.post("/api/games/export")
    def export(rules: PlayableRule):
        content, filename = export_package(rules)
        return Response(content, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    return app


app = create_app()
