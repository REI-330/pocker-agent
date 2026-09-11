from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from itertools import combinations

from .tools import CardRef, DeckTool, beats, classify


@dataclass
class DoudizhuState:
    hands: list[list[CardRef]]
    kitty: list[CardRef]
    current_player: int = 0
    landlord: int | None = None
    bid: int = 0
    last_play: Any = None
    last_player: int | None = None
    passes: int = 0
    finished: bool = False
    winners: list[int] | None = None
    scores: list[int] | None = None
    bombs: int = 0
    landlord_plays: int = 0
    farmer_plays: int = 0


class DoudizhuEngine:
    """Deterministic first-party engine composed around canonical card tools."""
    kind = "doudizhu"

    def __init__(self, rules, seed=0, player_count=None, tool_plan=None):
        if player_count not in (None, 3): raise ValueError("斗地主固定三人")
        self.rules, self.seed, self.events = rules, seed, []
        self.tool_plan = tool_plan or {}
        self._declared_tools = {item.get("name") for item in self.tool_plan.get("tools", []) if isinstance(item, dict)}
        from .tools.registry import default_registry
        config = next((item.get("config", {}) for item in self.tool_plan.get("tools", [])
                       if isinstance(item, dict) and item.get("name") == "doudizhu_settle"), {"player_count": 3})
        self._settlement_tool = default_registry().create("doudizhu_settle", **config)
        self._rank_tool = default_registry().create("doudizhu_hand_rank")
        self._climb_tool = default_registry().create("climb_beats")
        deck_config = next((item.get("config", {}) for item in self.tool_plan.get("tools", [])
                            if isinstance(item, dict) and item.get("name") == "deck"), {})
        self._deck_tool = default_registry().create("deck", **deck_config)
        self.state = None

    def tool_call(self, tool, operation, **payload):
        if self._declared_tools and tool not in self._declared_tools:
            raise ValueError(f"tool_not_declared:{tool}")
        self.events.append({"event": "tool_called", "tool": tool, "operation": operation, **payload})

    def setup(self):
        if self.state is not None: raise RuntimeError("game_already_started")
        ranks = [*map(str, range(3, 11)), "J", "Q", "K", "A", "2"]
        cards = self._deck_tool.cards()
        cards += [CardRef("BJ", "BJ", "", 15), CardRef("RJ", "RJ", "", 16)]
        import random
        random.Random(self.seed).shuffle(cards)
        self.state = DoudizhuState([cards[i*17:(i+1)*17] for i in range(3)], cards[51:54], scores=[0,0,0])
        self.tool_call("deck", "deal")
        self.events.append({"event":"game_started", "kind":self.kind})
        self.events.append({"event":"dealt", "kitty_count":3})
        return self.events

    def run(self, max_steps=1000):
        self.setup()
        for _ in range(max_steps):
            if self.state.finished:
                return self.events
            actions = self.legal_actions()
            if not actions:
                break
            # Deterministic baseline bot: bid highest immediately, then play
            # the first legal combination (or pass when required).
            action = (f"bid:{max(self.rules.bidding_values)}" if self.state.landlord is None
                      else actions[1] if actions and actions[0] == "pass" and len(actions) > 1 else actions[0])
            self.step(action)
        raise RuntimeError("simulation_step_limit: 斗地主牌局超过步数限制")

    def legal_actions(self):
        if self.state is None: return []
        if self.state.finished: return []
        if self.state.landlord is None: return [f"bid:{v}" for v in self.rules.bidding_values]
        actions = ["pass"] if self.state.last_play is not None else []
        for indices, candidate in self.legal_play_combinations():
            actions.append("play:" + ",".join(map(str, indices)))
        return actions

    def legal_play_combinations(self):
        hand = self.state.hands[self.state.current_player]
        seen = set()
        for size in range(1, min(20, len(hand)) + 1):
            for indices in combinations(range(len(hand)), size):
                try: candidate = self._rank_tool([hand[i] for i in indices])
                except ValueError: continue
                if candidate.key() in seen: continue
                if self.state.last_play is None or self._climb_tool(
                    current={"kind": candidate.kind, "rank": candidate.rank, "length": candidate.length},
                    previous={"kind": self.state.last_play.kind, "rank": self.state.last_play.rank, "length": self.state.last_play.length}):
                    seen.add(candidate.key()); yield indices, candidate

    def step(self, action: str | None = None, card_index=0, **kwargs):
        if self.state is None: self.setup()
        action = action or self.legal_actions()[0]
        if action == "play":
            action = "play:" + str(card_index)
        if action.startswith("bid:"):
            self.tool_call("turn_order", "bid")
            value = int(action.split(":",1)[1])
            if value not in self.rules.bidding_values: raise ValueError("invalid_bid")
            self.state.bid = max(self.state.bid, value)
            if value == max(self.rules.bidding_values) or self.state.current_player == 2:
                self.state.landlord = self.state.current_player
                self.state.hands[self.state.landlord].extend(self.state.kitty)
                self.state.current_player = self.state.landlord
                self.events.append({"event":"landlord_selected", "player":self.state.landlord, "bid":self.state.bid})
            else: self.state.current_player = (self.state.current_player + 1) % 3
            return self.events[-1]
        if action == "pass":
            self.tool_call("turn_order", "advance")
            self.state.passes += 1; self.state.current_player = (self.state.current_player + 1) % 3
            if self.state.passes >= 2: self.state.last_play = None; self.state.passes = 0
            return self.events.append({"event":"pass", "player":self.state.current_player}) or self.events[-1]
        if action.startswith("play:"):
            self.tool_call("doudizhu_hand_rank", "classify")
            self.tool_call("climb_beats", "compare")
            raw = action.split(":",1)[1]
            indices = sorted((int(v) for v in raw.split(",")), reverse=True)
            hand = self.state.hands[self.state.current_player]
            if not indices or any(i < 0 or i >= len(hand) for i in indices) or len(set(indices)) != len(indices): raise ValueError("card_index_out_of_range")
            selected = [hand[i] for i in reversed(indices)]
            hand_type = self._rank_tool(selected)
            if self.state.last_play:
                current = {"kind": hand_type.kind, "rank": hand_type.rank, "length": hand_type.length}
                previous = {"kind": self.state.last_play.kind, "rank": self.state.last_play.rank, "length": self.state.last_play.length}
                if not self._climb_tool(current=current, previous=previous): raise ValueError("play_does_not_beat")
            for i in indices: hand.pop(i)
            self.state.last_play, self.state.last_player, self.state.passes = hand_type, self.state.current_player, 0
            if hand_type.kind in {"bomb", "rocket"}: self.state.bombs += 1
            if self.state.current_player == self.state.landlord: self.state.landlord_plays += 1
            else: self.state.farmer_plays += 1
            event = {"event":"play", "player":self.state.current_player, "cards":[c.as_dict() for c in selected], "hand_type":hand_type.kind}
            if not hand:
                self.state.finished = True; self.state.winners = [self.state.current_player]
                spring = ((self.state.current_player == self.state.landlord and self.state.farmer_plays == 0)
                          or (self.state.current_player != self.state.landlord and self.state.landlord_plays <= 1))
                self.tool_call("doudizhu_settle", "settle")
                self.state.scores = self._settlement_tool.settle(self.state.bid, self.state.landlord,
                                                      self.state.current_player, bombs=self.state.bombs, spring=spring)
                event["event"] = "game_finished"; event["winner"] = f"player-{self.state.current_player + 1}"
            else: self.state.current_player = (self.state.current_player + 1) % 3
            self.events.append(event); return event
        raise ValueError("illegal_action")

    def serialize(self):
        lp = None if self.state.last_play is None else {"kind": self.state.last_play.kind, "rank": self.state.last_play.rank, "length": self.state.last_play.length, "wing": self.state.last_play.wing}
        return {"rules": self.rules.model_dump(mode="json"), "seed": self.seed, "events": self.events, "tool_plan": self.tool_plan,
                "state": {"hands":[[c.as_dict() for c in h] for h in self.state.hands], "kitty":[c.as_dict() for c in self.state.kitty],
                           "current_player":self.state.current_player, "landlord":self.state.landlord, "bid":self.state.bid,
                           "last_play": lp, "last_player": self.state.last_player, "passes": self.state.passes,
                           "finished":self.state.finished, "winners":self.state.winners, "scores":self.state.scores,
                           "bombs":self.state.bombs,"landlord_plays":self.state.landlord_plays,"farmer_plays":self.state.farmer_plays}}

    def view(self):
        s = self.state
        return {"kind": self.kind, "phase": "叫地主" if s.landlord is None else "出牌",
                "current_player": f"player-{s.current_player + 1}", "finished": s.finished,
                "winners": [f"player-{i + 1}" for i in (s.winners or [])],
                "players": [{"id": f"player-{i + 1}", "hand": [c.as_dict() for c in h] if i == 0 or s.finished else [],
                             "hidden_count": 0 if i == 0 or s.finished else len(h),
                             "score": s.scores[i] if s.scores else 0,
                             "role": "landlord" if i == s.landlord else "farmer"} for i, h in enumerate(s.hands)],
                "kitty": [c.as_dict() for c in s.kitty] if s.landlord is not None else [],
                "legal_actions": self.legal_actions(), "events": self.events[-100:]}
