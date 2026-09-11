"""Compatibility alias; canonical workspace lifecycle lives in application.workspace_service."""
import sys as _sys
from importlib import import_module as _import_module
_sys.modules[__name__] = _import_module("pocker_agent.application.workspace_service")
