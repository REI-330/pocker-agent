"""Compatibility child-process entry point for the relocated worker."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parent / "game_runtime" / "plugins" / "worker.py"), run_name="__main__")
else:
    import sys
    from importlib import import_module
    sys.modules[__name__] = import_module("pocker_agent.game_runtime.plugins.worker")
