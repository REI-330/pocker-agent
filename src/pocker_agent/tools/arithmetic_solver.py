"""Exact arithmetic tool backed by the validated expression evaluator."""
from dataclasses import dataclass, field

from ..arithmetic import calculate, solve
from .core import ToolError


@dataclass
class ArithmeticSolverTool:
    target: int = 24
    operations: tuple[str, ...] = ("+", "-", "*", "/")
    fractional: bool = True
    rank_values: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.operations = tuple(self.operations)
        if not self.operations or not set(self.operations) <= {"+", "-", "*", "/"}:
            raise ToolError("invalid_arithmetic_operations")

    def solve(self, numbers):
        return solve(tuple(self._values(numbers)), self.target, self.operations, self.fractional)

    def validate(self, expression, numbers):
        value = calculate(expression, self._values(numbers), self.operations, self.fractional)
        if value != self.target:
            raise ToolError(f"算式结果为{value}，目标是{self.target}；请重新尝试")
        return {"correct": True, "target": self.target}

    def _values(self, numbers):
        return [self.rank_values.get(getattr(number, "rank", ""), getattr(number, "value", number)) for number in numbers]
