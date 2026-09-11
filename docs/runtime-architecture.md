# Deterministic runtime boundaries

The backend is split into three dependency directions:

```text
agents / interfaces  ->  domain
agents / application ->  game_runtime -> domain
infrastructure       ->  domain (and is injected by application)
```

`pocker_agent.domain` contains rule contracts, generated-plugin schemas, DSL
validation, and deterministic value calculations. It has no dependency on an
LLM client, HTTP handlers, task workers, or persistence.

`pocker_agent.game_runtime` contains the deterministic game engines, tool
composition, isolated plugin VM, simulation, export, and session persistence
orchestration. The runtime accepts a validated `PlayableRule` and an optional
validated `ToolPlan`; it never decides how a rule was generated.

`pocker_agent.infrastructure` contains storage and host adapters. It is the
only layer allowed to know the filesystem/database details.

The original top-level modules (`runtime`, `engine`, `game_rules`, `tools`, and
others) are import shims. They are kept for existing clients and tests while
new code must use the canonical packages above. The shims alias the canonical
module object, so class identity and monkeypatch behaviour remain stable during
the migration.
