"""Interpret a ToolPlan flow without importing a gameplay engine."""
from copy import deepcopy
from types import SimpleNamespace

from .game_layer import GameLayer
from .rule_executor import RuleExecutor
from .tools.core import CardRef, ToolError, ToolResult
from .tools.plan import ToolPlan


def encode(value):
    if isinstance(value, CardRef):
        return {"$card": value.as_dict()}
    if isinstance(value, ToolResult):
        return {"$result": encode(value.value)}
    if isinstance(value, set):
        return {"$set": [encode(item) for item in value]}
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ToolError("flow_state_not_serializable")


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"$card"}:
            return CardRef(**value["$card"])
        if set(value) == {"$result"}:
            return ToolResult(decode(value["$result"]))
        if set(value) == {"$set"}:
            return set(decode(value["$set"]))
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode(item) for item in value]
    return value


class FlowRuntime:
    execution_mode = "tool_flow"

    def __init__(self, rules, seed=0, player_count=None, tool_plan=None):
        self.rules, self.seed = rules, seed
        self.plan = ToolPlan.model_validate(tool_plan)
        if self.plan.flow is None:
            raise ToolError("executable_flow_required")
        if player_count is not None and player_count != self.plan.players:
            raise ToolError("flow_player_count_mismatch")
        self.tool_plan = self.plan.model_dump(mode="json")
        self.kind = self.plan.game_kind
        self.layer = GameLayer.from_plan(self.plan)
        self.layer.context.state = deepcopy(self.plan.flow.initial)
        self.layer.context.state.update(seed=seed, input={})
        self.pc = self.plan.flow.entry
        self.started = False

    @property
    def events(self):
        return self.layer.context.events

    @property
    def state(self):
        state = self.layer.context.state
        return SimpleNamespace(finished=state.get("finished", False),
                               current_player=state.get("current_player", 0))

    def _advance(self):
        executor = RuleExecutor(self.layer)
        for _ in range(self.plan.flow.step_limit):
            node = self.plan.flow.nodes[self.pc]
            if node.kind == "call":
                executor.execute(node.action)
                self.events[-1]["flow_node"] = self.pc
                self.pc = node.next
            elif node.kind == "branch":
                value = executor._resolve(node.value)
                self.pc = next((case.target for case in node.cases
                                if type(value) is type(case.value) and value == case.value), node.next)
            elif node.kind == "wait":
                if self.state.finished:
                    raise ToolError("finished_flow_cannot_wait")
                return
            else:
                if not self.state.finished:
                    raise ToolError("flow_end_requires_finished_state")
                self.layer.context.emit("game_finished", winners=self.layer.context.state.get("winners", []))
                return
        raise ToolError("flow_step_limit")

    def setup(self):
        if self.started:
            raise ToolError("game_already_started")
        backup = deepcopy(self.layer)
        try:
            self.layer.context.emit("game_started", kind=self.kind, execution_mode=self.execution_mode)
            self._advance()
        except Exception:
            self.layer, self.pc = backup, self.plan.flow.entry
            raise
        self.started = True
        return self.events

    def legal_actions(self):
        node = self.plan.flow.nodes[self.pc]
        return list(node.inputs) if self.started and node.kind == "wait" and not self.state.finished else []

    def step(self, action=None, card_index=0, **payload):
        actions = self.legal_actions()
        action = action or (actions[0] if actions else None)
        if action not in actions:
            raise ToolError("illegal_action")
        backup, previous = deepcopy(self.layer), self.pc
        try:
            self.layer.context.state["input"] = {**payload, "action": action, "card_index": card_index}
            self.pc = self.plan.flow.nodes[self.pc].inputs[action]
            self._advance()
        except Exception:
            self.layer, self.pc = backup, previous
            raise
        return self.events[-1]

    def run(self, max_steps=1000):
        self.setup()
        for _ in range(max_steps):
            if self.state.finished:
                return self.events
            self.step()
        raise ToolError("simulation_step_limit")

    def serialize(self):
        return {"executor": "tool_flow", "rules": self.rules.model_dump(mode="json"),
                "seed": self.seed, "tool_plan": self.tool_plan, "pc": self.pc, "started": self.started,
                "context": encode(self.layer.context.state), "events": deepcopy(self.events),
                "tools": {name: encode(vars(tool)) for name, tool in self.layer.tools.items()}}

    @classmethod
    def restore(cls, rules, data):
        runtime = cls(rules, seed=data["seed"], tool_plan=data["tool_plan"])
        runtime.pc, runtime.started = data["pc"], data["started"]
        if runtime.pc not in runtime.plan.flow.nodes:
            raise ToolError("flow_saved_node_missing")
        runtime.layer.context.state = decode(data["context"])
        runtime.layer.context.events = deepcopy(data["events"])
        for name, values in data["tools"].items():
            vars(runtime.layer.tools[name]).update(decode(values))
        return runtime

    def view(self):
        state = self.layer.context.state
        visible = state.get("visible_counts", [0] * self.plan.players)
        reveal = self.state.finished or state.get("reveal", False)
        players = []
        for i, hand in enumerate(state.get("hands", [[] for _ in range(self.plan.players)])):
            shown = hand if reveal or i == 0 else hand[:visible[i]]
            players.append({"id": f"player-{i + 1}", "hand": [c.as_dict() for c in shown],
                            "hidden_count": len(hand) - len(shown), "score": state.get("scores", [0] * self.plan.players)[i]})
        return {"kind": self.kind, "execution_mode": self.execution_mode, "flow_node": self.pc,
                "round": state.get("round", 1), "max_rounds": state.get("max_rounds", 1),
                "phase": state.get("phase", self.pc), "current_player": f"player-{self.state.current_player + 1}",
                "human_player": "player-1", "finished": self.state.finished,
                "winners": [f"player-{i + 1}" for i in state.get("winners", [])],
                "finish_reason": state.get("finish_reason", ""), "legal_actions": self.legal_actions(),
                "players": players, "table": [], "deck_remaining": len(state.get("stock", [])),
                "feedback": state.get("feedback", ""), "events": self.events[-100:]}
