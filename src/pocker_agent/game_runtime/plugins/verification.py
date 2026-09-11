"""Runtime-only acceptance gate for generated plugin programs.

Keeping this importable without ``plugin_builder`` prevents the game runtime
from depending on the LLM/code-generation orchestration layer.
"""

from functools import lru_cache

from pocker_agent.game_runtime.plugins.sandbox import verify_plugin
from pocker_agent.domain.plugin_schema import PluginRule


@lru_cache(maxsize=32)
def accepted_program(serialized: str):
    return verify_plugin(PluginRule.model_validate_json(serialized))
