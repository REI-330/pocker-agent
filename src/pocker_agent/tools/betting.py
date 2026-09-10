from __future__ import annotations

from dataclasses import dataclass

from .core import ToolError


@dataclass
class PotTool:
    """Integer chip ledger. Contributions cover the whole hand, not a street."""

    stacks: list[int]
    committed: list[int] | None = None

    def __post_init__(self):
        self.stacks = list(self.stacks)
        self.committed = ([0] * len(self.stacks) if self.committed is None
                          else list(self.committed))
        if not self.stacks or len(self.stacks) != len(self.committed):
            raise ToolError("chip_ledger_size_mismatch")
        if any(type(n) is not int or n < 0 for n in self.stacks + self.committed):
            raise ToolError("chips_must_be_nonnegative_integers")

    def commit(self, player: int, amount: int) -> int:
        if type(player) is not int or not 0 <= player < len(self.stacks):
            raise ToolError("invalid_player")
        if type(amount) is not int or not 0 <= amount <= self.stacks[player]:
            raise ToolError("invalid_bet")
        self.stacks[player] -= amount
        self.committed[player] += amount
        return amount

    def pots(self, folded: set[int] | None = None) -> list[dict]:
        folded = set() if folded is None else set(folded)
        if not folded <= set(range(len(self.stacks))):
            raise ToolError("invalid_folded_player")
        result, previous = [], 0
        for level in sorted({x for x in self.committed if x > 0}):
            contributors = [i for i, value in enumerate(self.committed) if value >= level]
            # A sole contributor's unmatched excess is a refund, not a contested pot.
            result.append({"amount": (level - previous) * len(contributors),
                           "eligible_players": [i for i in contributors if i not in folded],
                           "refund_to": contributors[0] if len(contributors) == 1 else None})
            previous = level
        return result

    def distribute(self, winners: dict[int, list[int]], folded: set[int] | None = None,
                   *, odd_chip_order: list[int] | None = None) -> list[int]:
        """Pay every pot or fail. Keys are pot indexes, not dict insertion order.

        The caller supplies clockwise seats starting left of the dealer for odd
        chips. Uncalled excess is returned without a winner entry.
        """
        pots = self.pots(folded)
        order = list(range(len(self.stacks))) if odd_chip_order is None else list(odd_chip_order)
        if sorted(order) != list(range(len(self.stacks))):
            raise ToolError("invalid_odd_chip_order")
        required = {i for i, pot in enumerate(pots) if pot["refund_to"] is None}
        if set(winners) != required:
            raise ToolError("every_contested_pot_requires_winners")
        awards = [0] * len(self.stacks)
        for index, pot in enumerate(pots):
            if pot["refund_to"] is not None:
                awards[pot["refund_to"]] += pot["amount"]
                continue
            chosen = winners[index]
            if (not chosen or len(set(chosen)) != len(chosen)
                    or not set(chosen) <= set(pot["eligible_players"])):
                raise ToolError("ineligible_or_duplicate_pot_winner")
            share, remainder = divmod(pot["amount"], len(chosen))
            for offset, player in enumerate(i for i in order if i in chosen):
                awards[player] += share + int(offset < remainder)
        if sum(awards) != sum(self.committed):
            raise ToolError("chip_conservation_failed")
        return awards

