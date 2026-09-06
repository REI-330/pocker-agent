# Demo Architecture

```text
React Web UI
  -> FastAPI API
     -> Agent Orchestrator
        -> OpenAI-compatible LLM adapter
        -> Game Rule DSL parser/validator
        -> Rule Engine
           -> Simulation Runner
           -> Single-player Runtime
     -> Export Builder
  -> SQLite/local demo storage
```

The model adapter uses the Chat Completions-compatible `POST /chat/completions` contract. `base_url`, model, and API key are environment-configured, so a local gateway or another compatible provider can be used without changing the Agent state machine.

## Boundaries

- The LLM proposes structured rules and clarifications. It does not directly execute game actions.
- The DSL is the contract between agent output and deterministic execution.
- The rule engine owns legality, state transitions, scoring, and termination.
- The simulation runner emits inspectable events rather than only a final answer.
- The runtime consumes DSL and engine state to render a game.

## Extension path

Multiplayer can later reuse the rule engine with an authoritative server and add room/state synchronization. It is deliberately outside the demo boundary.
