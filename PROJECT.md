# Project Management

## Objective

Validate that Pocker Agent can convert a natural-language poker game idea into a validated, executable rule definition and a playable web game.

## Milestones

### M0: Repository and contracts

- [x] Confirm product scope and demo boundaries
- [x] Create repository documentation
- [ ] Define the first Game Rule DSL schema
- [ ] Define backend/frontend API contracts

### M1: Rule foundation

- [ ] Implement card, deck, player, turn, action, and score primitives
- [ ] Implement DSL parser and validation errors
- [ ] Implement deterministic rule engine
- [ ] Add simulation runner and execution event log

### M2: Agent loop

- [ ] Add OpenAI-compatible model client
- [ ] Implement clarification state machine
- [ ] Generate and repair DSL from model output
- [ ] Expose rule confirmation and simulation APIs

### M3: Web demo

- [ ] Build natural-language design workspace
- [ ] Build rule confirmation and DSL view
- [ ] Build simulation trace view
- [ ] Build single-player runtime
- [ ] Add DSL and Web game export

### M4: Verification

- [ ] Run a complete browser-to-backend vertical slice
- [ ] Document supported and unsupported rule constructs
- [ ] Record demo scenarios and known limitations

## Initial issues

1. Define DSL v0.1 and JSON Schema.
2. Implement deterministic poker primitives.
3. Implement rule validation and simulation events.
4. Implement model adapter and structured output parsing.
5. Build the design workspace UI.
6. Build the single-player runtime UI.
7. Add export packaging and demo documentation.

## Product constraints

- No login in the demo.
- Web only.
- Single-player play first; multiplayer is future work.
- No AI-generated visual assets.
- No moderation, rights management, or public marketplace in the demo.
- User input may describe broad rules, but unsupported executable constructs must be reported explicitly.
