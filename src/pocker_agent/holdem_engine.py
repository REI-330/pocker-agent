from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tools import (AllInTool, BettingRoundTool, CardRef, CommunityDealTool,
                    DeckTool, PhaseProgressTool, PotTool, ToolError,
                    settle_pots, showdown)


@dataclass
class HoldemState:
    hands: list[list[CardRef]]
    deck: list[CardRef]
    board: list[CardRef]
    stacks: list[int]
    committed: list[int]
    hand_committed: list[int]
    folded: set[int]
    current_player: int = 0
    street: str = "preflop"
    finished: bool = False
    winners: list[int] | None = None
    acted: set[int] = field(default_factory=set)
    last_raise: int = 0


class HoldemEngine:
    kind = "holdem"

    def __init__(self, rules, seed=0, player_count=None, tool_plan=None):
        count = rules.players.min_players if player_count is None else player_count
        if not rules.players.min_players <= count <= rules.players.max_players: raise ValueError("invalid_player_count")
        self.rules, self.seed, self.player_count, self.events, self.state = rules, seed, count, [], None
        self.tool_plan = tool_plan or {}
        self._declared_tools = {item.get("name") for item in self.tool_plan.get("tools", [])
                                if isinstance(item, dict)}
        from .tools.registry import default_registry
        self._registry = default_registry()
        self._deck = self._registry.create("deck", ranks=rules.deck.ranks, suits=rules.deck.suits)
        self._all_in = self._registry.create("all_in")
        self._phase = self._registry.create("phase_progress", phases=list(rules.streets))
        self._community = self._registry.create("community_deal", burn=True)
        self._showdown = self._registry.create("showdown")
        self._settle_pots = self._registry.create("settle_pots")

    def setup(self):
        if self.state is not None: raise RuntimeError("game_already_started")
        n = self.player_count
        dealt = self._deck.deal(self.seed, n, 2, 0).value
        hands = dealt["hands"]
        cards = dealt["deck"]
        self._tool_event("deck", "deal")
        stacks = [self.rules.starting_chips] * n; committed = [0] * n
        committed[0] = min(self.rules.small_blind, stacks[0]); stacks[0] -= committed[0]
        committed[1 % n] = min(self.rules.big_blind, stacks[1 % n]); stacks[1 % n] -= committed[1 % n]
        self.state = HoldemState(hands, cards, [], stacks, committed, list(committed), set(), current_player=2 % n)
        self.events.append({"event":"game_started", "kind":self.kind, "street":"preflop"})
        return self.events

    def run(self, max_steps=1000):
        self.setup()
        for _ in range(max_steps):
            if self.state.finished: return self.events
            self.step()
        raise RuntimeError("simulation_step_limit: 德州牌局超过步数限制")

    def _active(self):
        """Players still eligible to win the hand, including all-in players."""
        return [i for i in range(len(self.state.hands)) if i not in self.state.folded]
    def _to_call(self): return max(self.state.committed) - self.state.committed[self.state.current_player]

    def legal_actions(self):
        if self.state is None or self.state.finished: return []
        if len(self._active()) <= 1: return ["showdown"]
        try:
            return self._betting_tool().legal_actions()
        except ToolError:
            return []

    def _tool_event(self, tool: str, operation: str) -> None:
        """Record a deterministic ToolPlan call without exposing private cards."""
        if self._declared_tools and tool not in self._declared_tools:
            raise ToolError(f"tool_not_declared:{tool}")
        self.events.append({"event": "tool_called", "tool": tool, "operation": operation})

    def _betting_tool(self) -> BettingRoundTool:
        return BettingRoundTool(
            self.state.stacks,
            self.state.committed,
            self.state.hand_committed,
            set(self.state.folded),
            self.state.current_player,
            min_raise=self.rules.big_blind,
            acted=set(getattr(self.state, "acted", set())),
            last_raise=getattr(self.state, "last_raise", 0),
        )

    def _sync_betting_state(self, tool: BettingRoundTool) -> None:
        self.state.stacks = list(tool.stacks)
        self.state.committed = list(tool.committed)
        self.state.hand_committed = list(tool.hand_committed)
        self.state.folded = set(tool.folded)
        self.state.current_player = tool.current_player
        self.state.acted = set(tool.acted)
        self.state.last_raise = tool.last_raise

    def step(self, action=None, card_index=0, amount=None, **kwargs):
        if self.state is None: self.setup()
        action = action or self.legal_actions()[0]
        if action not in self.legal_actions(): raise ValueError("illegal_action:" + action)
        if action == "showdown": return self._finish()
        p = self.state.current_player
        betting = self._betting_tool()
        try:
            betting.act(action, amount=amount, player=p)
        except ToolError as exc:
            raise ValueError(str(exc)) from exc
        self._sync_betting_state(betting)
        self._tool_event("betting_round", "act")
        self.events.append({"event":"action", "player":p, "action":action, "street":self.state.street})
        if len(self._active()) <= 1: return self._finish()
        all_in = self._all_in.check(self.state.stacks, self.state.folded)
        self._tool_event("all_in", "check")
        if all_in["runout_required"]:
            while not self.state.finished and self.state.street != "river":
                self._advance_street()
            if not self.state.finished: return self._finish()
        elif betting.is_complete():
            return self._advance_street()
        return self.events[-1]

    def _advance_street(self):
        phases = list(self.rules.streets)
        phase = PhaseProgressTool(phases, phases.index(self.state.street))
        if phase.finished(): return self._finish()
        next_state = phase.advance()
        self._tool_event("phase_progress", "advance")
        self._community.deal(self.state.deck, self.state.board, next_state["phase"])
        self._tool_event("community_deal", "deal")
        self.state.street = next_state["phase"]
        self.state.committed = [0] * len(self.state.hands)
        self.state.acted = set(self.state.folded)
        self.state.last_raise = 0
        self.state.current_player = self._first_actionable()
        self.events.append({"event":"street_started", "street":self.state.street, "board_count":len(self.state.board)})
        return self.events[-1]

    def _first_actionable(self) -> int:
        for p in range(len(self.state.hands)):
            if p not in self.state.folded and self.state.stacks[p] > 0:
                return p
        return 0

    def _finish(self):
        active = self._active();
        ranks = None
        if len(active) == 1: winners = active
        else:
            if len(self.state.board) < 5:
                raise ValueError("showdown_requires_five_board_cards")
            result = self._showdown(hands=self.state.hands, board=self.state.board, active=active)
            self._tool_event("showdown", "call")
            ranks = result["ranks"]
            winners = list(result["winners"])
        # Resolve each main/side pot independently. Folded players contribute
        # chips but cannot win; uncalled excess is refunded by the settlement
        # tool.
        ledger = PotTool([0] * len(self.state.hands), self.state.hand_committed)
        pots = ledger.pots(self.state.folded)
        pot_winners = {}
        if len(active) == 1:
            for index, pot in enumerate(pots):
                if pot["refund_to"] is None:
                    pot_winners[index] = active
        else:
            for index, pot in enumerate(pots):
                eligible = [i for i in pot["eligible_players"] if i in ranks]
                if eligible:
                    best = max(ranks[i] for i in eligible)
                    pot_winners[index] = [i for i in eligible if ranks[i] == best]
        settlement = self._settle_pots(stacks=self.state.stacks, hand_committed=self.state.hand_committed,
                                       winners=pot_winners, folded=self.state.folded)
        self._tool_event("settle_pots", "call")
        self.state.stacks = list(settlement["stacks"])
        self.state.finished, self.state.winners = True, winners
        event = {"event":"game_finished", "winners":winners,
                 "winner": winners[0] if len(winners) == 1 else None}; self.events.append(event); return event

    def view(self):
        s=self.state
        ledger = PotTool([0] * len(s.hands), s.hand_committed)
        current_bet = max(s.committed) if s.committed else 0
        return {"kind":self.kind,"round":1,"max_rounds":1,"phase":s.street,"finish_reason":"completed" if s.finished else "","street":s.street,"board":[c.as_dict() for c in s.board],"table":[],"deck_remaining":len(s.deck),"current_player":f"player-{s.current_player+1}","finished":s.finished,"winners":[f"player-{i+1}" for i in (s.winners or [])],"pot":sum(s.hand_committed),"current_bet":current_bet,"to_call":self._to_call() if not s.finished else 0,"side_pots":ledger.pots(s.folded),"players":[{"id":f"player-{i+1}","hand":[c.as_dict() for c in h] if i==0 or s.finished else [],"hidden_count":0 if i==0 or s.finished else 2,"chips":s.stacks[i],"committed":s.committed[i],"hand_committed":s.hand_committed[i],"score":0,"folded":i in s.folded} for i,h in enumerate(s.hands)],"legal_actions":self.legal_actions(),"events":self.events[-100:]}

    def serialize(self):
        s=self.state; cv=lambda c:c.as_dict()
        return {"rules":self.rules.model_dump(mode="json"),"seed":self.seed,"events":self.events,"tool_plan":self.tool_plan,"state":{"hands":[[cv(c) for c in h] for h in s.hands],"deck":[cv(c) for c in s.deck],"board":[cv(c) for c in s.board],"stacks":s.stacks,"committed":s.committed,"hand_committed":s.hand_committed,"folded":list(s.folded),"current_player":s.current_player,"street":s.street,"finished":s.finished,"winners":s.winners,"acted":sorted(s.acted),"last_raise":s.last_raise}}
