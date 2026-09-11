from .holdem import BettingRoundTool, AllInTool, CommunityDealTool, PhaseProgressTool, showdown, settle_pots
from .betting import PotTool
from .core import ToolError


class HoldemTurnTool:
    """Execute one complete betting decision and its deterministic transitions."""
    def __init__(self, streets=("preflop", "flop", "turn", "river"), min_raise=20):
        self.streets, self.min_raise = tuple(streets), min_raise

    def act(self, state, action, amount=None):
        active = [i for i in range(len(state["hands"])) if i not in set(state.get("folded", []))]
        if len(active) <= 1 or state.get("finished"): raise ToolError("holdem_finished")
        betting = BettingRoundTool(state["stacks"], state["committed"], state["hand_committed"],
            set(state.get("folded", [])), state["current_player"], min_raise=self.min_raise,
            acted=set(state.get("acted", [])), last_raise=state.get("last_raise", 0))
        betting.act(action, amount=amount, player=state["current_player"])
        state.update(stacks=list(betting.stacks), committed=list(betting.committed),
                     hand_committed=list(betting.hand_committed), folded=list(betting.folded),
                     current_player=betting.current_player, acted=list(betting.acted), last_raise=betting.last_raise)
        if len([i for i in range(len(state["hands"])) if i not in set(state.get("folded", []))]) <= 1:
            return self._finish(state)
        all_in = AllInTool().check(state["stacks"], set(state.get("folded", [])))
        if all_in["runout_required"]:
            while state["street"] != "river": self._advance(state)
            return self._finish(state)
        if betting.is_complete(): return self._advance(state)
        return {"action": action, "street": state["street"], "finished": False}

    def _advance(self, state):
        phase = PhaseProgressTool(list(self.streets), self.streets.index(state["street"]))
        if phase.finished(): return self._finish(state)
        next_street = phase.advance()["phase"]
        CommunityDealTool(burn=True).deal(state["deck"], state["board"], next_street)
        state.update(street=next_street, phase=next_street, committed=[0] * len(state["hands"]),
                     acted=list(state.get("folded", [])), last_raise=0,
                     current_player=next(i for i in range(len(state["hands"]))
                                         if i not in set(state.get("folded", [])) and state["stacks"][i] > 0))
        return {"street": next_street, "finished": False}

    def _finish(self, state):
        active = [i for i in range(len(state["hands"])) if i not in set(state.get("folded", []))]
        if len(active) == 1:
            winners, ranks = active, None
        else:
            if len(state["board"]) < 5: raise ToolError("showdown_requires_five_board_cards")
            result = showdown(state["hands"], state["board"], active); winners, ranks = result["winners"], result["ranks"]
        ledger = PotTool([0] * len(state["hands"]), state["hand_committed"])
        pots = ledger.pots(set(state.get("folded", []))); pot_winners = {}
        for index, pot in enumerate(pots):
            if pot.get("refund_to") is not None: continue
            eligible = active if ranks is None else [i for i in pot["eligible_players"] if i in ranks]
            if eligible:
                best = max(ranks[i] for i in eligible) if ranks is not None else 0
                pot_winners[index] = eligible if ranks is None else [i for i in eligible if ranks[i] == best]
        result = settle_pots(state["stacks"], state["hand_committed"], pot_winners, set(state.get("folded", [])))
        state.update(stacks=list(result["stacks"]), finished=True, winners=list(winners), phase="finished")
        return {"finished": True, "winners": list(winners)}
