# Pocker Agent

Pocker Agent is a web-based agent framework for designing and playing new poker games from natural-language rules.

## Demo goal

The first demo validates this flow:

```text
Natural-language rules -> agent clarification -> Game Rule DSL
-> simulation -> single-player play -> Web export + DSL JSON export
```

The demo uses a reusable poker deck and table UI. Core game behavior is executed by a deterministic rule engine; an LLM is used for intent recognition, clarification, and DSL generation.

## Planned stack

- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Rule engine and simulation: Python
- Persistence: SQLite/local files for the demo
- Model integration: OpenAI-compatible API configured through environment variables

## Project documents

- [Demo product specification](docs/product/demo-spec.md)
- [Architecture](docs/architecture.md)
- [Roadmap](PROJECT.md)
- [Contributing](CONTRIBUTING.md)

## Local development

Install dependencies and run the focused test suite:

```powershell
uv sync
uv run pytest -q
```

Start the API locally:

```powershell
uv run uvicorn pocker_agent.api:app --app-dir src --reload
```

The first vertical slice exposes:

- `GET /health`
- `POST /api/rules/validate`
- `POST /api/simulations?seed=0`

The current DSL and engine are v0.1 contracts. The API accepts a complete DSL fixture; the natural-language Agent loop and Web UI are the next milestones.

Agent configuration is read from environment variables. Copy `.env.example` into your local environment and set an OpenAI-compatible API key:

```powershell
$env:POCKER_AGENT_API_KEY = "your-key"
$env:POCKER_AGENT_BASE_URL = "https://api.openai.com/v1"
$env:POCKER_AGENT_MODEL = "gpt-4o-mini"
```

Agent endpoints:

- `POST /api/agent/turn` accepts `{ "message": "...", "messages": [], "proposal": null }` and returns a question, proposal, or validation error.
- `POST /api/agent/confirm` validates the returned proposal before simulation.
