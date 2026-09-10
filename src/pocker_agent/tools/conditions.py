from __future__ import annotations
from .core import ToolError

def evaluate(condition: str, *, hand_size=None, deck_size=None, score=None, target=None, legal_actions=None, passes=None):
    required = {"hand_empty": [hand_size], "deck_empty": [deck_size], "target_score": [score, target],
                "no_legal_action": [legal_actions], "passes_reached": [passes, target]}
    if condition not in required: raise ToolError("unknown_end_condition:" + condition)
    if any(value is None for value in required[condition]): raise ToolError("condition_input_missing")
    values = {"hand_empty": hand_size == 0, "deck_empty": deck_size == 0,
              "target_score": score is not None and target is not None and score >= target,
              "no_legal_action": not legal_actions, "passes_reached": passes is not None and target is not None and passes >= target}
    if condition not in values: raise ToolError("unknown_end_condition:" + condition)
    return values[condition]
