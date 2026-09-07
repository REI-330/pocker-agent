"""Adapter: generated logic owns transitions; host owns validation and visibility."""

from .engine import Card, GameState, PlayerState
from .family_engines import FamilyEngine
from .plugin_builder import accepted_program
from .plugin_sandbox import execute, shuffled_deck, simulate_plugin, validate_frame
from .plugin_schema import card_catalog


class PluginEngine(FamilyEngine):
    def setup(self):
        if self.events:
            raise ValueError("game_already_started")
        accepted_program(self.rules.model_dump_json())
        frame = execute(
            self.rules,
            "setup",
            deck=shuffled_deck(self.rules, self.seed),
            players=len(self.state.players),
        )
        self._apply(frame)
        self.emit("game_started", kind="plugin")
        if self.state.finished:
            self.finish(self.state.winners, "generated_rule")
        return self.events

    def _apply(self, frame):
        value, choices = validate_frame(self.rules, frame)
        self.extra = {
            "program_state": value.model_dump(mode="json"),
            "program_actions": [a.model_dump(exclude_none=True) for a in choices],
        }
        catalog = card_catalog(self.rules)

        def cards(ids):
            return [Card(**catalog[id]) for id in ids]

        self.state = GameState(
            1,
            value.phase,
            value.current_player,
            [
                PlayerState(f"player-{i + 1}", cards(hand), value.scores[i])
                for i, hand in enumerate(value.hands)
            ],
            deck=cards(value.deck),
            finished=value.finished,
            winners=[f"player-{i + 1}" for i in value.winners],
            finish_reason="generated_rule" if value.finished else "",
        )

    def legal_actions(self):
        return [
            f"choice_{i}" for i, _ in enumerate(self.extra.get("program_actions", []))
        ]

    def step(self, action_name=None, card_index=0, **kwargs):
        actions = self.legal_actions()
        if not actions:
            raise ValueError("game_finished")
        action = (
            action_name
            if action_name is not None
            else actions[(self.seed + len(self.events) * 17) % len(actions)]
        )
        self.require(action)
        if len(self.events) >= self.rules.max_steps + 1:
            raise ValueError("plugin_step_limit: 牌局超过约定动作上限")
        player = self.state.players[self.state.current_player].id
        internal_action = self.extra["program_actions"][actions.index(action)]["id"]
        frame = execute(
            self.rules,
            "step",
            state=self.extra["program_state"],
            action_id=internal_action,
        )
        self._apply(frame)
        event = self.emit("action_executed", player=player, action=action)
        if self.state.finished:
            self.finish(self.state.winners, "generated_rule")
        return event

    def run(self, max_steps=1000):
        accepted_program(self.rules.model_dump_json())
        trace = simulate_plugin(self.rules, self.seed)
        self._apply(trace[0])
        self.emit("game_started", kind="plugin")
        for frame in trace[1:]:
            self._apply(frame)
            self.emit("action_executed", action=frame["action"]["id"])
        self.finish(self.state.winners, "generated_rule")
        return self.events

    def view(self):
        # Generated programs never supply HTML or public snapshots. Only card
        # positions/labels are exposed; raw data, seed and opponent IDs stay server-side.
        return {
            "kind": "plugin",
            "phase": self.state.phase,
            "table": [],
            "players": [
                {
                    "id": p.id,
                    "score": p.score,
                    "hand": [c.as_dict() for c in p.hand]
                    if i == 0 or self.state.finished
                    else [],
                    "hidden_count": len(p.hand) if i and not self.state.finished else 0,
                }
                for i, p in enumerate(self.state.players)
            ],
            "plugin_actions": [
                {
                    **a,
                    "id": f"choice_{i}",
                    "label": f"从玩家{a['target_player'] + 1}抽第{a['card_index'] + 1}张牌"
                    if a.get("target_player") is not None
                    else a["label"],
                }
                for i, a in enumerate(self.extra.get("program_actions", []))
            ],
            "instructions": "按规则选择下方合法动作；其他玩家由电脑操作。",
            "events": self.events[-100:],
        }
