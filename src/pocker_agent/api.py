from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import AgentSession, RuleAgent
from .llm import OpenAICompatibleClient
from .models import GameRuleDSL
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


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
