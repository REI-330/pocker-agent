"""A reference composition: orchestration is data, all operations are registered tools."""


def holdem_plan(rules):
    count = rules.players.max_players
    blinds = [min(rules.small_blind, rules.starting_chips), min(rules.big_blind, rules.starting_chips)] + [0] * (count - 2)

    def call(tool, operation, args, result, next_node):
        return {"kind": "call", "action": {"tool": tool, "operation": operation,
                "args": args, "result_key": result}, "next": next_node}

    def update(values, next_node):
        return call("state", "update", {"state": "$state", "values": values}, None, next_node)

    def branch(value, yes, no):
        return {"kind": "branch", "value": value, "cases": [{"value": True, "target": yes}], "next": no}

    nodes = {
        "deal": call("deck", "deal", {"seed": "$state.seed", "hands": count, "cards_each": 2}, "deal", "init"),
        "init": update({"hands": "$state.deal.hands", "deck": "$state.deal.deck"}, "inspect_betting"),
        "inspect_betting": call("betting_round", "inspect", {"state": "$state"}, "betting", "apply_betting"),
        "apply_betting": update("$state.betting", "active_players"),
        "active_players": call("all_in", "check", {"stacks": "$state.stacks", "folded": "$state.folded"}, "active", "single_winner"),
        "single_winner": branch("$state.active.single_winner", "uncontested", "round_complete"),
        "round_complete": branch("$state.complete", "phase_status", "wait"),
        "wait": {"kind": "wait", "inputs": {a: "act" for a in rules.actions},
                 "available_actions": "$state.legal_actions", "default_action": "$state.default_action"},
        "act": call("betting_round", "transition", {"state": "$state", "action": "$state.input.action",
                    "amount": "$state.input.amount"}, "betting", "apply_betting"),
        "phase_status": call("phase_progress", "inspect", {"current": "$state.street"}, "progress", "last_phase"),
        "last_phase": branch("$state.progress.finished", "showdown", "next_phase"),
        "next_phase": call("phase_progress", "successor", {"current": "$state.street"}, "progress", "apply_phase"),
        "apply_phase": update({"street": "$state.progress.phase", "phase": "$state.progress.phase"}, "community"),
        "community": call("community_deal", "deal", {"deck": "$state.deck", "board": "$state.board",
                          "street": "$state.street"}, "community", "reset_betting"),
        "reset_betting": call("betting_round", "start_round", {"state": "$state", "first_seat": 1 if count == 2 else 0}, "betting", "apply_betting"),
        "uncontested": update({"result": {"winners": "$state.active.active_players", "ranks": None}}, "pot_winners"),
        "showdown": call("showdown", "call", {"hands": "$state.hands", "board": "$state.board",
                         "eligible": "$state.active.active_players"}, "result", "pot_winners"),
        "pot_winners": call("pot_winners", "call", {"contributions": "$state.hand_committed", "folded": "$state.folded",
                            "eligible": "$state.active.active_players", "ranks": "$state.result.ranks"}, "pot_winners", "settle"),
        "settle": call("settle_pots", "call", {"stacks": "$state.stacks", "hand_committed": "$state.hand_committed",
                        "winners": "$state.pot_winners", "folded": "$state.folded"}, "settlement", "finish"),
        "finish": update({"stacks": "$state.settlement.stacks", "side_pots": "$state.settlement.pots",
                         "awards": "$state.settlement.awards", "pot": 0, "finished": True,
                         "phase": "finished", "winners": "$state.result.winners"}, "end"),
        "end": {"kind": "end"},
    }
    tools = [
        {"name": "deck", "config": {"ranks": rules.deck.ranks, "suits": rules.deck.suits}},
        {"name": "zones"}, {"name": "hand_rank", "config": {"best_of": 7}},
        {"name": "state"}, {"name": "betting_round", "config": {"stacks": [rules.starting_chips] * count, "min_raise": rules.big_blind}},
        {"name": "phase_progress", "config": {"phases": list(rules.streets)}},
        {"name": "community_deal"}, {"name": "all_in"}, {"name": "showdown"},
        {"name": "pot_winners"}, {"name": "settle_pots"},
    ]
    return {"schema_version": "1.0", "game_kind": "holdem", "players": count,
            "tools": tools, "phases": list(rules.streets), "requirements": [],
            "flow": {"entry": "deal", "initial": {
                "stacks": [rules.starting_chips - blind for blind in blinds],
                "committed": blinds, "hand_committed": blinds,
                "finished": False, "winners": [], "current_player": 2 % count,
                "street": rules.streets[0], "phase": rules.streets[0], "board": [],
                "folded": [], "acted": [], "last_raise": 0,
            }, "nodes": nodes}}
