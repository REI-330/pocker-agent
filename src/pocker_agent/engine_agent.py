"""Compatibility import for the relocated tool planning agent."""

import sys

from .agents import tool_planner as _implementation

sys.modules[__name__] = _implementation
