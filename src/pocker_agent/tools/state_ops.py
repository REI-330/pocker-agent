"""Game-independent state and expression operations used by flow programs."""
from copy import deepcopy
import operator

from .core import ToolError, DeckTool
from ..arithmetic import solve
from .matching import matches


class StateTool:
    def update(self, state: dict, values: dict):
        if any(key in {"input", "seed"} or key.startswith("_") for key in values):
            raise ToolError("reserved_state_field")
        state.update(deepcopy(values))
        return sorted(values)


class LogicTool:
    def evaluate(self, expression, _depth=0):
        if _depth > 32:
            raise ToolError("expression_depth_limit")
        if not isinstance(expression, dict):
            return expression
        if len(expression) != 1:
            raise ToolError("invalid_expression")
        op, arguments = next(iter(expression.items()))
        if not isinstance(arguments, list):
            raise ToolError("expression_arguments_must_be_list")
        args = [self.evaluate(value, _depth + 1) for value in arguments]
        binary = {"eq": operator.eq, "lt": operator.lt, "le": operator.le,
                  "gt": operator.gt, "ge": operator.ge, "add": operator.add}
        if op in binary and len(args) == 2:
            return binary[op](*args)
        if op == "all":
            return all(args)
        if op == "any":
            return any(args)
        if op == "not" and len(args) == 1:
            return not args[0]
        if op == "count" and len(args) == 1:
            return len(args[0])
        raise ToolError("unknown_expression_operation")


class PointContestTool:
    """Compare bounded point totals with optional short-hand priority.

    Busted players are ineligible; a priority exact-target hand outranks an
    ordinary total. The caller explicitly supplies any bust-precedence policy.
    """
    def resolve(self, totals: list[int], sizes: list[int], target: int,
                priority_size: int = 2, first_bust_loses: bool = False):
        if len(totals) != len(sizes) or len(totals) < 2:
            raise ToolError("invalid_point_contest")
        if first_bust_loses and totals[0] > target:
            return [1]
        ranks = [(total <= target, total == target and size == priority_size, total)
                 for total, size in zip(totals, sizes)]
        eligible = [i for i, total in enumerate(totals) if total <= target]
        if not eligible:
            return []
        best = max(ranks[i] for i in eligible)
        return [i for i in eligible if ranks[i] == best]


class DealerPolicyTool:
    """Reusable bounded point-hand policy; owns drawing, not a game engine."""
    def play(self, stock, hand, hand_rank, stand_on: int = 17, hits_soft: bool = True):
        if not callable(hand_rank):
            raise ToolError("invalid_hand_rank_tool")
        draws = 0
        while True:
            rank = hand_rank(hand)
            if rank["total"] > 21 or rank["total"] > stand_on or (rank["total"] == stand_on and not (hits_soft and rank["soft"])):
                return {"total": rank["total"], "soft": rank["soft"], "draws": draws}
            if not stock:
                raise ToolError("deck_exhausted")
            hand.append(stock.pop())
            draws += 1


class ArithmeticDealTool:
    """Deal a solvable arithmetic hand without a gameplay engine."""
    def __init__(self, ranks, suits, target, operations=("+", "-", "*", "/"), fractional=True, rank_values=None):
        self.deck = DeckTool(ranks, suits)
        self.target, self.operations, self.fractional = target, tuple(operations), fractional
        self.rank_values = rank_values or {}

    def deal(self, seed, cards_each=4):
        import random
        for attempt in range(64):
            cards = self.deck.shuffled(f"{seed}:{attempt}")
            hand, stock = cards[:cards_each], cards[cards_each:]
            numbers = [self.rank_values.get(card.rank, card.value) for card in hand]
            if solve(tuple(numbers), self.target, self.operations, self.fractional) is not None:
                return {"hand": hand, "stock": stock, "numbers": numbers}
        raise ToolError("no_solvable_deal")


class SheddingTurnTool:
    """Execute one draw/play turn against shared state."""
    def __init__(self, wild_rank=None, recycle=True):
        self.wild_rank, self.recycle = wild_rank, recycle

    def play(self, state, action, card_index=0, declared_suit=""):
        hands, current = state["hands"], state["current_player"]
        hand, table = hands[current], state.get("table", [])
        top = table[-1] if table else None
        if action == "play":
            if type(card_index) is not int or not 0 <= card_index < len(hand):
                raise ToolError("card_index_out_of_range")
            card = hand[card_index]
            if top is not None and not matches(card, top, active_suit=state.get("active_suit"), wild_ranks={self.wild_rank} if self.wild_rank else set()):
                raise ToolError("card_does_not_match")
            hand.pop(card_index); table.append(card)
            state["active_suit"] = declared_suit if self.wild_rank and card.rank == self.wild_rank and declared_suit else card.suit
            if not hand:
                state.update(finished=True, winners=[current], phase="finished", finish_reason="hand_empty")
                return {"action": "play", "finished": True, "player": current}
        elif action == "draw":
            if not state.get("stock") and self.recycle and len(table) > 1:
                state["stock"] = list(table[:-1]); state["table"] = table[-1:]
            if not state.get("stock"): raise ToolError("deck_exhausted")
            hand.append(state["stock"].pop())
        elif action != "pass":
            raise ToolError("illegal_shedding_action")
        state["current_player"] = (current + 1) % len(hands)
        return {"action": action, "finished": False, "player": current}
