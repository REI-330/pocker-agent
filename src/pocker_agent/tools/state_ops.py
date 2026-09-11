"""Game-independent state and expression operations used by flow programs."""
from copy import deepcopy
import operator

from .core import ToolError


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
