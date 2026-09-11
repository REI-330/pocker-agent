"""Compatibility import for the relocated model infrastructure adapter."""

import sys

from .infrastructure import llm as _implementation

sys.modules[__name__] = _implementation
