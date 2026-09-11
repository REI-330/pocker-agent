"""Compatibility alias; import from pocker_agent.game_runtime.tools.holdem in new code."""

import sys as _sys
from importlib import import_module as _import_module

_sys.modules[__name__] = _import_module("pocker_agent.game_runtime.tools.holdem")
