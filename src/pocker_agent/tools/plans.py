from __future__ import annotations

from typing import Any


def plan_for_rules(rules: Any) -> dict[str, Any]:
    """Derive the host-owned composition plan from an executable rule object."""
    kind = getattr(rules, "kind", "legacy")
    deck = rules.deck
    base = {"schema_version": "1.0", "game_kind": kind, "players": rules.players.max_players,
            "phases": [p.name for p in getattr(rules, "phases", [])], "requirements": []}
    if kind == "blackjack":
        from ..flow_plans.blackjack import blackjack_plan
        return blackjack_plan(rules)
    elif kind == "holdem":
        players = [f"player-{i + 1}" for i in range(rules.players.max_players)]
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "zones"},
                          {"name": "pot", "config": {"stacks": [rules.starting_chips] * rules.players.max_players}},
                          {"name": "betting_round", "config": {"stacks": [rules.starting_chips] * rules.players.max_players,
                                                                       "min_raise": rules.big_blind}},
                          {"name": "phase_progress", "config": {"phases": list(rules.streets)}},
                          {"name": "community_deal"}, {"name": "all_in"},
                          {"name": "showdown"}, {"name": "settle_pots"},
                          {"name": "hand_rank", "config": {"best_of": 7}}]
        base["actions"] = [{"tool": "deck", "operation": "deal",
                             "args": {"seed": 0, "hands": len(players), "cards_each": 2},
                             "result_key": "deal"}]
        for index, player in enumerate(players):
            base["actions"].append({"tool": "zones", "operation": "create",
                                     "args": {"name": player, "cards": f"$state.deal.hands.{index}", "visible_to": [player]}})
        base["actions"].append({"tool": "zones", "operation": "create",
                                 "args": {"name": "community", "cards": "$state.deal.kitty", "visible_to": ["*"]}})
        base["end_conditions"] = ["phase_progress.finished", "all_in.runout_required", "showdown.completed"]
    elif kind == "doudizhu":
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "doudizhu_hand_rank", "config": {}},
                          {"name": "climb_beats", "config": {}}, {"name": "doudizhu_settle", "config": {"player_count": 3}},
                          {"name": "turn_order", "config": {"players": [f"player-{i + 1}" for i in range(base["players"])]}}, {"name": "winner_resolve"}, {"name": "score_settle"}]
    elif kind == "shedding":
        players = [f"player-{i + 1}" for i in range(base["players"])]
        hand_size = getattr(rules.players, "starting_hand_size", 5)
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "zones"}, {"name": "draw_discard"},
                          {"name": "card_match"}, {"name": "turn_order", "config": {"players": players}},
                          {"name": "shedding_turn", "config": {"wild_rank": rules.wild_rank, "recycle": rules.recycle_discard}}, {"name": "state"},
                          {"name": "win_condition"}, {"name": "winner_resolve"}, {"name": "score_settle"}]
        base["flow"] = {"entry": "deal", "initial": {"finished": False, "winners": [], "current_player": 0, "phase": "play"}, "nodes": {
            "deal": {"kind": "call", "next": "init", "action": {"tool": "deck", "operation": "deal", "args": {"seed": "$state.seed", "hands": len(players), "cards_each": hand_size, "kitty": 1}, "result_key": "deal"}},
            "init": {"kind": "call", "next": "wait", "action": {"tool": "state", "operation": "update", "args": {"state": "$state", "values": {"hands": "$state.deal.hands", "stock": "$state.deal.deck", "table": "$state.deal.kitty"}}}},
            "wait": {"kind": "wait", "inputs": {"play": "turn", "draw": "turn", "pass": "turn"}},
            "turn": {"kind": "call", "next": "branch", "action": {"tool": "shedding_turn", "operation": "play", "args": {"state": "$state", "action": "$state.input.action", "card_index": "$state.input.card_index", "declared_suit": "$state.input.declared_suit"}, "result_key": "turn_result"}},
            "branch": {"kind": "branch", "value": "$state.finished", "cases": [{"value": True, "target": "end"}], "next": "wait"},
            "end": {"kind": "end"},
        }}
        base["actions"] = [{"tool": "deck", "operation": "deal",
                             "args": {"seed": 0, "hands": len(players), "cards_each": hand_size, "kitty": 1},
                             "result_key": "deal"},
                            {"tool": "zones", "operation": "create",
                             "args": {"name": "stock", "cards": "$state.deal.deck"}},
                            {"tool": "zones", "operation": "create",
                             "args": {"name": "table", "cards": "$state.deal.kitty", "visible_to": ["*"]}}]
    elif kind == "arithmetic":
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "arithmetic_deal", "config": {"ranks": deck.ranks, "suits": deck.suits, "target": rules.target, "operations": rules.operations, "fractional": rules.fractional_intermediates, "rank_values": rules.rank_values}},
                          {"name": "arithmetic_solver", "config": {"target": rules.target, "operations": rules.operations,
                                                                         "fractional": rules.fractional_intermediates,
                                                                         "rank_values": rules.rank_values}}, {"name": "state"}, {"name": "score_settle"}]
        call = lambda tool, operation, args=None, result_key=None: {"tool": tool, "operation": operation,
                                                                     "args": args or {}, **({"result_key": result_key} if result_key else {})}
        update = lambda values: call("state", "update", {"state": "$state", "values": values})
        base["flow"] = {"entry": "deal", "initial": {"finished": False, "winners": [], "scores": [0], "current_player": 0},
            "nodes": {
                "deal": {"kind": "call", "next": "init", "action": call("arithmetic_deal", "deal", {"seed": "$state.seed", "cards_each": rules.card_count}, "deal")},
                "init": {"kind": "call", "next": "wait", "action": update({"table": "$state.deal.hand", "stock": "$state.deal.stock", "numbers": "$state.deal.numbers", "phase": "solve"})},
                "wait": {"kind": "wait", "inputs": {"submit_expression": "route", "no_solution": "no_solution", "give_up": "give_up"}},
                "route": {"kind": "branch", "value": "$state.input.action", "cases": [{"value": "submit_expression", "target": "validate"}], "next": "give_up"},
                "validate": {"kind": "call", "next": "correct", "action": call("arithmetic_solver", "validate", {"expression": "$state.input.expression", "numbers": "$state.table"}, "solution")},
                "correct": {"kind": "call", "next": "finish_score", "action": call("score_settle", "call", {"scores": "$state.scores", "winners": [0], "points": 1}, "scores")},
                "finish_score": {"kind": "call", "next": "end", "action": update({"finished": True, "winners": [0], "phase": "finished"})},
                "no_solution": {"kind": "call", "next": "no_solution_finish", "action": call("arithmetic_solver", "solve", {"numbers": "$state.table"}, "solution")},
                "no_solution_finish": {"kind": "call", "next": "finish_score", "action": update({"finished": True, "winners": [0], "phase": "finished"})},
                "give_up": {"kind": "call", "next": "end", "action": update({"finished": True, "winners": [0], "phase": "finished"})},
                "end": {"kind": "end"},
            }}
    else:
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "turn_order", "config": {"players": [f"player-{i + 1}" for i in range(base["players"])]}}]
    return base
