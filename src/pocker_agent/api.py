from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import GameRuleDSL
from .simulation import simulate
from .validation import validate_dsl

app = FastAPI(title="Pocker Agent", version="0.1.0")


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
