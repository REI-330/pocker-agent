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

The implementation is being built in milestones. Setup commands will be added with the first runnable vertical slice.
