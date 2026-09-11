from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .tools import ToolContext, ToolError
from .game_layer import GameLayer
from .tools.core import ToolResult
from .tools.core import CardRef

@dataclass
class RuleExecutor:
    """Execute only declared ToolAction operations through a GameLayer."""
    layer: GameLayer

    def execute(self, action: Any) -> Any:
        if hasattr(action, "model_dump"): action = action.model_dump(mode="python")
        if not isinstance(action, dict): raise ToolError("invalid_tool_action")
        tool_name, operation = action.get("tool"), action.get("operation")
        tool = self.layer.tools.get(tool_name)
        if tool is None or not isinstance(operation, str) or operation.startswith("_"):
            raise ToolError("tool_operation_not_allowed")
        method = getattr(tool, operation, None)
        if not callable(method):
            # Configured function tools use the stable operation name `call`.
            if operation != "call" or not callable(tool): raise ToolError("unknown_tool_operation")
            method = tool
        args = self._resolve(action.get("args", {}))
        if not isinstance(args, dict): raise ToolError("tool_args_must_be_object")
        try: result = method(**args)
        except (TypeError, ValueError) as exc: raise ToolError("tool_call_rejected") from exc
        key = action.get("result_key")
        if key: self.layer.context.state[key] = result
        self.layer.context.emit("tool_called", tool=tool_name, operation=operation, result_key=key)
        return result

    def _resolve(self, value: Any) -> Any:
        """Resolve only `$state.foo.bar` references; never evaluates code."""
        if isinstance(value, str) and value == "$state":
            return self.layer.context.state
        if isinstance(value, str) and (value.startswith("$state.") or value.startswith("$tool.")):
            if value.startswith("$state."):
                current: Any = self.layer.context.state
                path = value[7:]
            else:
                current = self.layer.tools
                path = value[6:]
            for part in path.split("."):
                if isinstance(current, ToolResult): current = current.value
                if isinstance(current, dict) and part in current: current = current[part]
                elif isinstance(current, dict) and part in self.layer.tools: current = self.layer.tools[part]
                elif hasattr(current, part) and not part.startswith("_"): current = getattr(current, part)
                elif isinstance(current, (list, tuple)) and part.isdigit() and int(part) < len(current): current = current[int(part)]
                else: raise ToolError("state_reference_not_found")
            return current.value if isinstance(current, ToolResult) else current
        if isinstance(value, dict): return {key: self._resolve(item) for key, item in value.items()}
        if isinstance(value, list): return [self._resolve(item) for item in value]
        return value

    def run(self) -> dict[str, Any]:
        results = [self.execute(action) for action in self.layer.plan.get("actions", [])]
        tool_state = {}
        for name, tool in self.layer.tools.items():
            if hasattr(tool, "zones"): tool_state[name] = {"zones": tool.zones, "visibility": tool.visibility}
            elif hasattr(tool, "stock") and hasattr(tool, "discard"): tool_state[name] = {"stock": tool.stock, "discard": tool.discard}
        return {"results": self._jsonable(results), "state": self._jsonable(self.layer.context.state), "tool_state": self._jsonable(tool_state), "events": self.layer.context.events}

    @classmethod
    def _jsonable(cls, value: Any) -> Any:
        if isinstance(value, ToolResult): return cls._jsonable(value.value)
        if isinstance(value, CardRef): return value.as_dict()
        if isinstance(value, dict): return {str(k): cls._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)): return [cls._jsonable(v) for v in value]
        if isinstance(value, set): return sorted(cls._jsonable(v) for v in value)
        return value
