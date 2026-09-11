"""Compatibility import for the relocated code generation agent."""

import sys

from .agents import code_builder as _implementation

sys.modules[__name__] = _implementation
