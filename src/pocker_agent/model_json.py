"""Compatibility alias; canonical parser lives in infrastructure.model_json."""
import sys as _sys
from importlib import import_module as _import_module
_sys.modules[__name__] = _import_module("pocker_agent.infrastructure.model_json")
