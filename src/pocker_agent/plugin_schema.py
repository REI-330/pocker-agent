"""Data-only interface for generated programs; no executable Python is accepted."""

from typing import Any, Literal

from pydantic import Field, model_validator

from .models import DeckSpec, StrictSpec


class PluginPlayers(StrictSpec):
    min_players: int = Field(ge=2, le=4)
    max_players: int = Field(ge=2, le=4)
    starting_hand_size: Literal[0] = 0

    @model_validator(mode="after")
    def fixed_count(self):
        if self.min_players != self.max_players:
            raise ValueError("生成代码的首版协议要求固定玩家数")
        return self


class PluginState(StrictSpec):
    hands: list[list[str]] = Field(min_length=2, max_length=4)
    deck: list[str]
    discard: list[str]
    current_player: int = Field(ge=0, le=3)
    finished: bool
    winners: list[int] = Field(max_length=4)
    scores: list[int | float] = Field(min_length=2, max_length=4)
    phase: str = Field(min_length=1, max_length=120)
    data: dict[str, Any] = Field(default_factory=dict)


class PluginAction(StrictSpec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_:-]+$", max_length=64)
    label: str = Field(min_length=1, max_length=80)
    # Hidden-card choices expose a position, never the hidden identity.
    target_player: int | None = Field(default=None, ge=0, le=3)
    card_index: int | None = Field(default=None, ge=0, le=107)


class Scenario(StrictSpec):
    name: str = Field(min_length=1, max_length=120)
    state: PluginState
    action_id: str = Field(pattern=r"^[a-zA-Z0-9_:-]+$", min_length=1, max_length=64)
    expected: dict[str, Any] = Field(min_length=1, max_length=20)


class PluginPlan(StrictSpec):
    game_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=100)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    deck: DeckSpec
    excluded_cards: list[str] = Field(default_factory=list, max_length=52)
    players: PluginPlayers
    max_rounds: Literal[1] = 1
    requirements: list[str] = Field(min_length=3, max_length=20)
    scenarios: list[Scenario] = Field(min_length=3, max_length=8)
    max_steps: int = Field(default=400, ge=10, le=600)

    @model_validator(mode="after")
    def card_contract(self):
        if self.deck.copies != 1:
            raise ValueError("生成插件当前要求一副牌，牌ID为rank+suit")
        ids = [r + s for r in self.deck.ranks for s in self.deck.suits]
        if len(ids) != len(set(ids)) or len(ids) > 108:
            raise ValueError("牌ID必须唯一，总牌数最多108")
        if len(set(self.excluded_cards)) != len(self.excluded_cards) or not set(
            self.excluded_cards
        ) <= set(ids):
            raise ValueError("排除牌必须是牌组内的不重复ID")
        if len(ids) - len(self.excluded_cards) < self.players.min_players:
            raise ValueError("剩余牌数小于玩家数")
        return self


class PluginRule(PluginPlan):
    schema_version: Literal["0.3"] = "0.3"
    kind: Literal["plugin"] = "plugin"
    source: str = Field(min_length=20, max_length=40000)


def card_catalog(plan):
    return {
        r + s: {"rank": r, "suit": s, "value": i + 1}
        for i, r in enumerate(plan.deck.ranks)
        for s in plan.deck.suits
        if r + s not in plan.excluded_cards
    }
