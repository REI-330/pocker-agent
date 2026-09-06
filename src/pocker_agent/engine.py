from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .models import GameRuleDSL


@dataclass(frozen=True)
class Card:
    suit: str
    rank: str
    value: int

    def as_dict(self) -> dict[str, Any]:
        return {"suit": self.suit, "rank": self.rank, "value": self.value}


@dataclass
class PlayerState:
    id: str
    hand: list[Card] = field(default_factory=list)
    score: int = 0
    active: bool = True


@dataclass
class GameState:
    round_number: int
    phase: str
    current_player: int
    players: list[PlayerState]
    table: list[Card] = field(default_factory=list)
    deck: list[Card] = field(default_factory=list)
    finished: bool = False


def build_deck(rules: GameRuleDSL) -> list[Card]:
    return [
        Card(suit=suit, rank=rank, value=index + 1)
        for _ in range(rules.deck.copies)
        for index, rank in enumerate(rules.deck.ranks)
        for suit in rules.deck.suits
    ]


class RuleEngine:
    """Small deterministic executor for DSL v0.1."""

    def __init__(self, rules: GameRuleDSL, seed: int = 0, player_count: int | None = None):
        count = player_count or rules.players.min_players
        if not rules.players.min_players <= count <= rules.players.max_players:
            raise ValueError("player_count is outside the DSL player range")
        self.rules = rules
        self.random = random.Random(seed)
        deck = build_deck(rules)
        self.random.shuffle(deck)
        self.state = GameState(
            round_number=1,
            phase=rules.phases[0].name,
            current_player=0,
            players=[PlayerState(id=f"player-{index + 1}") for index in range(count)],
            deck=deck,
        )
        self.events: list[dict[str, Any]] = []

    def _emit(self, event: str, **payload: Any) -> dict[str, Any]:
        record = {"event": event, "round": self.state.round_number, **payload}
        self.events.append(record)
        return record

    def setup(self) -> list[dict[str, Any]]:
        self._emit("game_started", phase=self.state.phase, players=[p.id for p in self.state.players])
        for player in self.state.players:
            for _ in range(self.rules.players.starting_hand_size):
                self._draw_to(player)
        return self.events

    def _draw_to(self, player: PlayerState) -> Card:
        if not self.state.deck:
            raise RuntimeError("deck_exhausted")
        card = self.state.deck.pop()
        player.hand.append(card)
        self._emit("card_drawn", player=player.id, card=card.as_dict())
        return card

    def legal_actions(self) -> list[str]:
        phase = next(p for p in self.rules.phases if p.name == self.state.phase)
        player = self.state.players[self.state.current_player]
        result: list[str] = []
        for action in self.rules.actions:
            if action.name not in phase.actions:
                continue
            if action.source == "hand" and not player.hand:
                continue
            if action.name == "draw" and not self.state.deck:
                continue
            result.append(action.name)
        return result

    def step(self, action_name: str | None = None) -> dict[str, Any]:
        if self.state.finished:
            raise RuntimeError("game_finished")
        legal = self.legal_actions()
        if not legal:
            return self.finish()
        action_name = action_name or legal[0]
        if action_name not in legal:
            raise ValueError(f"illegal_action:{action_name}")
        player = self.state.players[self.state.current_player]
        action = next(a for a in self.rules.actions if a.name == action_name)
        if action_name == "draw":
            card = self._draw_to(player)
            result = self._emit("action_executed", player=player.id, action=action_name, card=card.as_dict())
        elif action_name in {"play", "discard"}:
            card = player.hand.pop(0)
            self.state.table.append(card)
            result = self._emit("action_executed", player=player.id, action=action_name, card=card.as_dict())
        elif action_name == "pass":
            result = self._emit("action_executed", player=player.id, action=action_name)
        else:
            raise ValueError(f"unsupported_action:{action_name}")
        self.state.current_player = (self.state.current_player + 1) % len(self.state.players)
        self._maybe_finish()
        return result

    def _maybe_finish(self) -> None:
        if self.state.round_number >= self.rules.max_rounds and all(not player.hand for player in self.state.players):
            self.finish()

    def finish(self) -> dict[str, Any]:
        if self.state.finished:
            return self.events[-1]
        self.state.finished = True
        winner = max(self.state.players, key=lambda player: sum(card.value for card in player.hand) + player.score)
        return self._emit("game_finished", winner=winner.id, scores={p.id: p.score for p in self.state.players})

    def run(self, max_steps: int = 1000) -> list[dict[str, Any]]:
        self.setup()
        for _ in range(max_steps):
            if self.state.finished:
                break
            self.step()
        if not self.state.finished:
            self.finish()
        return self.events
