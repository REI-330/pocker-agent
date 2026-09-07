"""Child-process entry point. Never register Python callbacks in the JS runtime.

This is a resource-bounded JS VM, not an OS sandbox against native VM exploits.
The generated program receives only JSON and has no filesystem/network bindings.
"""

import json
import sys

import quickjs


def invoke(source, method, args):
    ctx = quickjs.Context()
    ctx.set_memory_limit(32 * 1024 * 1024)
    ctx.set_max_stack_size(512 * 1024)
    ctx.set_time_limit(0.2)
    # All entropy comes from the host's shuffled cards. A new VM per transition
    # also prevents unpersisted globals from becoming hidden game state.
    ctx.eval(
        "Math.random = () => { throw Error('Use supplied shuffled deck'); }; globalThis.Date = undefined;"
    )
    ctx.eval("globalThis.game = (" + source + "\n);")
    arguments = json.dumps(args, ensure_ascii=True, allow_nan=False)
    value = ctx.eval(
        "JSON.stringify(game[" + json.dumps(method) + "](..." + arguments + "))"
    )
    if not isinstance(value, str) or len(value) > 200000:
        raise ValueError("plugin_output_limit_or_missing_json")
    return json.loads(value)


def run(payload):
    source, catalog = payload["source"], payload["catalog"]

    def actions(state):
        return invoke(source, "actions", [state, catalog])

    if payload["mode"] == "actions":
        return actions(payload["state"])
    if payload["mode"] == "setup":
        state = invoke(source, "setup", [payload["deck"], payload["players"], catalog])
        return {"state": state, "actions": actions(state)}
    if payload["mode"] == "step":
        state = payload["state"]
        choices = actions(state)
        choice = next((a for a in choices if a["id"] == payload["action_id"]), None)
        if choice is None:
            raise ValueError("illegal_plugin_action")
        result = invoke(source, "step", [state, choice, catalog])
        return {"state": result, "actions": actions(result)}
    if payload["mode"] == "simulate":
        state = invoke(source, "setup", [payload["deck"], payload["players"], catalog])
        trace = [{"state": state, "actions": actions(state)}]
        for i in range(payload["max_steps"]):
            if state["finished"]:
                return trace
            choices = trace[-1]["actions"]
            if not choices:
                raise ValueError("active_state_without_actions")
            choice = choices[(payload["seed"] + i * 17) % len(choices)]
            state = invoke(source, "step", [state, choice, catalog])
            trace.append({"state": state, "actions": actions(state), "action": choice})
            if len(json.dumps(trace)) > 3_000_000:
                raise ValueError("plugin_trace_limit")
        if not state["finished"]:
            raise ValueError("plugin_step_limit: game did not terminate")
        return trace
    raise ValueError("unknown_worker_operation")


if __name__ == "__main__":
    try:
        result = run(json.loads(sys.stdin.read(500000)))
        print(json.dumps({"result": result}, ensure_ascii=True, allow_nan=False))
    except Exception as error:
        # This is the process protocol boundary; all failures are surfaced to
        # the parent and the repair loop, never treated as a successful game.
        print(json.dumps({"error": str(error)[:1500]}, ensure_ascii=True))
