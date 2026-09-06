from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from .agent import AgentSession, RuleAgent
from .llm import OpenAICompatibleClient
from .models import GameRuleDSL
from .runtime import RuntimeStore, export_package, snapshot
from .simulation import simulate
from .validation import validate_dsl

app = FastAPI(title="Pocker Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
agent = RuleAgent(OpenAICompatibleClient.from_env())
runtime_store = RuntimeStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0", "model_configured": str(bool(agent.model.api_key)).lower()}


@app.post("/api/agent/config")
def configure_agent(payload: dict) -> dict[str, str]:
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise HTTPException(status_code=400, detail="api_key is required")
    agent.model.api_key = api_key.strip()
    if isinstance(payload.get("base_url"), str) and payload["base_url"].strip():
        agent.model.base_url = payload["base_url"].strip().rstrip("/")
    if isinstance(payload.get("model"), str) and payload["model"].strip():
        agent.model.model = payload["model"].strip()
    return {"status": "configured", "model": agent.model.model, "base_url": agent.model.base_url}


@app.post("/api/agent/models")
def list_agent_models(payload: dict) -> dict:
    if isinstance(payload.get("api_key"), str) and payload["api_key"].strip():
        agent.model.api_key = payload["api_key"].strip()
    if isinstance(payload.get("base_url"), str) and payload["base_url"].strip():
        agent.model.base_url = payload["base_url"].strip().rstrip("/")
    try:
        models = agent.model.list_models()
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"models": models, "base_url": agent.model.base_url}


@app.post("/api/agent/test-connection")
def test_agent_connection(payload: dict) -> dict:
    if isinstance(payload.get("api_key"), str) and payload["api_key"].strip():
        agent.model.api_key = payload["api_key"].strip()
    if isinstance(payload.get("base_url"), str) and payload["base_url"].strip():
        agent.model.base_url = payload["base_url"].strip().rstrip("/")
    try:
        models = agent.model.list_models()
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True, "model": agent.model.model, "model_count": len(models)}


@app.post("/api/rules/validate")
def validate_rules(payload: dict) -> dict:
    rules, errors = validate_dsl(payload)
    return {"valid": not errors, "errors": errors, "rules": rules.model_dump(mode="json") if rules else None}


@app.post("/api/simulations")
def run_simulation(rules: GameRuleDSL, seed: int = 0, player_count: int | None = None) -> dict:
    try:
        result = simulate(rules, seed=seed, player_count=player_count)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"seed": result.seed, "completed": result.completed, "winner": result.winner, "events": result.events}


@app.post("/api/agent/turn")
def agent_turn(payload: dict) -> dict:
    session = AgentSession(messages=payload.get("messages", []), proposal=payload.get("proposal"))
    user_text = payload.get("message", "")
    if not isinstance(user_text, str) or not user_text.strip():
        raise HTTPException(status_code=400, detail="message is required")
    try:
        result = agent.turn(session, user_text)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"kind": result.kind, "message": result.message, "missing": result.missing, "errors": result.errors, "rules": result.rules.model_dump(mode="json") if result.rules else None, "messages": session.messages, "proposal": session.proposal}


@app.post("/api/agent/confirm")
def agent_confirm(payload: dict) -> dict:
    session = AgentSession(messages=payload.get("messages", []), proposal=payload.get("proposal"))
    result = agent.confirm(session)
    return {"kind": result.kind, "message": result.message, "errors": result.errors, "rules": result.rules.model_dump(mode="json") if result.rules else None}


@app.post("/api/runtime/sessions")
def create_runtime_session(rules: GameRuleDSL, seed: int = 0) -> dict:
    session = runtime_store.create(rules, seed=seed)
    return snapshot(session)


@app.post("/api/runtime/sessions/{session_id}/actions/{action_name}")
def execute_runtime_action(session_id: str, action_name: str) -> dict:
    try:
        session = runtime_store.get(session_id)
        event = session.engine.step(action_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"event": event, "state": snapshot(session)}


@app.post("/api/games/export")
def export_game(rules: GameRuleDSL) -> Response:
    content, filename = export_package(rules)
    return Response(content=content, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
