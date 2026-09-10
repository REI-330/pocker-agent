from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .core import CardRef, ToolError
from .ranking import best_of
from .betting import PotTool


@dataclass
class BettingRoundTool:
    """Deterministic, game-agnostic betting-round state machine.

    ``stacks`` are chips remaining at the table, while ``committed`` is the
    contribution in the current round and ``hand_committed`` is the whole-hand
    ledger used by side-pot settlement.  The caller owns persistence and can
    pass the result of :meth:`state` through a ToolPlan.
    """

    stacks: list[int]
    committed: list[int] | None = None
    hand_committed: list[int] | None = None
    folded: set[int] = field(default_factory=set)
    current_player: int = 0
    min_raise: int = 1
    acted: set[int] = field(default_factory=set)
    last_raise: int = 0

    def __post_init__(self) -> None:
        self.stacks = list(self.stacks)
        n = len(self.stacks)
        self.committed = [0] * n if self.committed is None else list(self.committed)
        self.hand_committed = list(self.committed) if self.hand_committed is None else list(self.hand_committed)
        if not n or len(self.committed) != n or len(self.hand_committed) != n:
            raise ToolError("chip_ledger_size_mismatch")
        if any(type(x) is not int or x < 0 for x in self.stacks + self.committed + self.hand_committed):
            raise ToolError("chips_must_be_nonnegative_integers")
        if type(self.min_raise) is not int or self.min_raise <= 0:
            raise ToolError("invalid_min_raise")
        self._check_player(self.current_player)
        self.folded = set(self.folded)
        self.acted = set(self.acted)
        if not self.folded <= set(range(n)) or not self.acted <= set(range(n)):
            raise ToolError("invalid_player")

    def _check_player(self, player: int) -> None:
        if type(player) is not int or not 0 <= player < len(self.stacks):
            raise ToolError("invalid_player")

    def _live(self) -> list[int]:
        return [i for i in range(len(self.stacks)) if i not in self.folded]

    def _actionable(self) -> list[int]:
        # A player with no chips left is all-in and must not receive a turn.
        return [i for i in self._live() if self.stacks[i] > 0]

    def current_bet(self) -> int:
        return max(self.committed, default=0)

    def to_call(self, player: int | None = None) -> int:
        p = self.current_player if player is None else player
        self._check_player(p)
        return max(0, self.current_bet() - self.committed[p])

    def legal_actions(self, player: int | None = None) -> list[str]:
        p = self.current_player if player is None else player
        self._check_player(p)
        if self.is_complete() or p != self.current_player or p in self.folded or self.stacks[p] <= 0:
            return []
        actions = ["check" if self.to_call(p) == 0 else "call"]
        if self.stacks[p] > self.to_call(p):
            actions.append("raise")
        actions.extend(["all_in", "fold"])
        return actions

    def is_complete(self) -> bool:
        live = self._live()
        if len(live) <= 1:
            return True
        actionable = self._actionable()
        if not actionable:
            return True
        current_bet = self.current_bet()
        return all(i in self.acted and self.committed[i] == current_bet for i in actionable)

    def _next_actionable(self, after: int) -> int:
        n = len(self.stacks)
        for offset in range(1, n + 1):
            p = (after + offset) % n
            if p not in self.folded and self.stacks[p] > 0 and p not in self.acted:
                return p
        # A caller can still explicitly advance a round with uneven stacks;
        # choose the first live, non-all-in player as a stable fallback.
        for offset in range(1, n + 1):
            p = (after + offset) % n
            if p not in self.folded and self.stacks[p] > 0:
                return p
        return after

    def _commit_to(self, player: int, target: int) -> int:
        self._check_player(player)
        if type(target) is not int or target < self.committed[player]:
            raise ToolError("invalid_bet_target")
        available = self.committed[player] + self.stacks[player]
        if target > available:
            raise ToolError("insufficient_chips")
        amount = target - self.committed[player]
        self.stacks[player] -= amount
        self.committed[player] = target
        self.hand_committed[player] += amount
        return amount

    def act(self, action: str, amount: int | None = None, player: int | None = None) -> dict[str, Any]:
        """Apply one action and return a JSON-safe state snapshot.

        ``amount`` for ``raise`` is the player's *total* contribution for this
        street, which avoids ambiguous increment-vs-target semantics in an
        Agent-generated plan. ``all_in`` always targets the player's full stack.
        """
        p = self.current_player if player is None else player
        self._check_player(p)
        if p != self.current_player:
            raise ToolError("not_current_player")
        if action not in self.legal_actions(p):
            raise ToolError("illegal_action")
        before_bet = self.current_bet()
        to_call = self.to_call(p)
        if action == "fold":
            self.folded.add(p)
            self.acted.add(p)
        elif action == "check":
            if to_call:
                raise ToolError("check_requires_no_call")
            self.acted.add(p)
        elif action == "call":
            self._commit_to(p, before_bet)
            self.acted.add(p)
        elif action == "raise":
            target = before_bet + self.min_raise if amount is None else amount
            if target <= before_bet:
                raise ToolError("raise_must_increase_bet")
            delta = target - before_bet
            if delta < self.min_raise:
                raise ToolError("raise_below_minimum")
            self._commit_to(p, target)
            self.last_raise = delta
            # A raise reopens action for every other actionable player.
            self.acted = {p} | {i for i in self.folded if i != p}
        elif action == "all_in":
            target = self.committed[p] + self.stacks[p]
            self._commit_to(p, target)
            self.acted.add(p)
            if target > before_bet:
                self.last_raise = target - before_bet
                self.acted = {p} | {i for i in self.folded if i != p}
        self.current_player = self._next_actionable(p)
        return self.state()

    def reset(self, *, current_player: int | None = None) -> dict[str, Any]:
        """Start a fresh betting street without touching whole-hand chips."""
        self.committed = [0] * len(self.stacks)
        self.acted = set(self.folded)
        self.last_raise = 0
        if current_player is not None:
            self._check_player(current_player)
            self.current_player = current_player
        else:
            self.current_player = self._next_actionable(self.current_player)
        return self.state()

    def state(self) -> dict[str, Any]:
        return {
            "stacks": list(self.stacks),
            "committed": list(self.committed),
            "hand_committed": list(self.hand_committed),
            "folded": sorted(self.folded),
            "acted": sorted(self.acted),
            "current_player": self.current_player,
            "current_bet": self.current_bet(),
            "to_call": self.to_call() if self._actionable() and not self.is_complete() else 0,
            "last_raise": self.last_raise,
            "complete": self.is_complete(),
            "legal_actions": self.legal_actions(),
        }


@dataclass
class PhaseProgressTool:
    """Finite phase/streets tool shared by betting and non-card games."""

    phases: list[str]
    index: int = 0

    def __post_init__(self) -> None:
        self.phases = list(self.phases)
        if not self.phases or len(set(self.phases)) != len(self.phases):
            raise ToolError("invalid_phases")
        if type(self.index) is not int or not 0 <= self.index < len(self.phases):
            raise ToolError("invalid_phase_index")

    def current(self) -> str:
        return self.phases[self.index]

    def finished(self) -> bool:
        return self.index == len(self.phases) - 1

    def advance(self, steps: int = 1) -> dict[str, Any]:
        if type(steps) is not int or steps < 1:
            raise ToolError("invalid_phase_steps")
        self.index = min(len(self.phases) - 1, self.index + steps)
        return self.state()

    def reset(self) -> dict[str, Any]:
        self.index = 0
        return self.state()

    def state(self) -> dict[str, Any]:
        return {"phase": self.current(), "index": self.index, "phases": list(self.phases), "finished": self.finished()}


@dataclass
class CommunityDealTool:
    """Deal public cards from a mutable deck into a mutable board."""

    burn: bool = True

    def deal(self, deck: list[CardRef], board: list[CardRef], street: str | int) -> dict[str, Any]:
        count = {"flop": 3, "turn": 1, "river": 1}.get(street, street if isinstance(street, int) else None)
        if type(count) is not int or count < 1:
            raise ToolError("invalid_community_deal")
        if len(deck) < count + (1 if self.burn else 0):
            raise ToolError("deck_exhausted")
        burned = deck.pop() if self.burn else None
        cards = [deck.pop() for _ in range(count)]
        board.extend(cards)
        return {"dealt": cards, "burned": burned, "board": list(board), "board_count": len(board)}


@dataclass
class AllInTool:
    """Detect when no further player decision is required."""

    def check(self, stacks: Sequence[int], folded: Iterable[int] | None = None) -> dict[str, Any]:
        folded_set = set() if folded is None else set(folded)
        if any(type(x) is not int or x < 0 for x in stacks):
            raise ToolError("chips_must_be_nonnegative_integers")
        if not folded_set <= set(range(len(stacks))):
            raise ToolError("invalid_folded_player")
        active = [i for i in range(len(stacks)) if i not in folded_set]
        actionable = [i for i in active if stacks[i] > 0]
        return {"active_players": active, "actionable_players": actionable,
                "all_in": bool(active) and not actionable, "runout_required": len(active) > 1 and not actionable,
                "single_winner": len(active) == 1}

    def call(self, stacks: Sequence[int], folded: Iterable[int] | None = None) -> dict[str, Any]:
        return self.check(stacks, folded)


def showdown(hands: Sequence[Sequence[CardRef]], board: Sequence[CardRef], eligible: Iterable[int] | None = None) -> dict[str, Any]:
    """Evaluate eligible players with best-five-of-seven (or fewer) cards."""
    chosen = list(range(len(hands))) if eligible is None else list(eligible)
    if not chosen or any(type(i) is not int or not 0 <= i < len(hands) for i in chosen):
        raise ToolError("invalid_showdown_players")
    ranks = {i: best_of(list(hands[i]) + list(board)) for i in chosen}
    strongest = max(ranks.values())
    return {"ranks": ranks, "winners": [i for i in chosen if ranks[i] == strongest], "best_rank": strongest}


def settle_pots(stacks: Sequence[int], hand_committed: Sequence[int], winners: dict[int, list[int]], folded: Iterable[int] | None = None) -> dict[str, Any]:
    """Build and distribute main/side pots as one declarative operation."""
    ledger = PotTool(list(stacks), list(hand_committed))
    awards = ledger.distribute(winners, set() if folded is None else set(folded))
    return {"pots": ledger.pots(set() if folded is None else set(folded)), "awards": awards,
            "stacks": [stack + award for stack, award in zip(stacks, awards)]}
