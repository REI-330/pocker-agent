from __future__ import annotations

from typing import Any


def plan_for_rules(rules: Any) -> dict[str, Any]:
    """Derive the host-owned composition plan from an executable rule object."""
    kind = getattr(rules, "kind", "legacy")
    deck = rules.deck
    base = {"schema_version": "1.0", "game_kind": kind, "players": rules.players.max_players,
            "phases": [p.name for p in getattr(rules, "phases", [])], "requirements": []}
    if kind == "blackjack":
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "hand_rank", "config": {"target": 21}},
                          {"name": "condition", "config": {}}, {"name": "winner_resolve"}, {"name": "score_settle"}]
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
                          {"name": "condition"}, {"name": "winner_resolve"}, {"name": "score_settle"}]
        base["actions"] = [{"tool": "deck", "operation": "deal",
                             "args": {"seed": 0, "hands": len(players), "cards_each": hand_size, "kitty": 1},
                             "result_key": "deal"},
                            {"tool": "zones", "operation": "create",
                             "args": {"name": "stock", "cards": "$state.deal.deck"}},
                            {"tool": "zones", "operation": "create",
                             "args": {"name": "table", "cards": "$state.deal.kitty", "visible_to": ["*"]}}]
    elif kind == "arithmetic":
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "arithmetic_solver", "config": {"target": rules.target}}]
    else:
        base["tools"] = [{"name": "deck", "config": {"ranks": deck.ranks, "suits": deck.suits}},
                          {"name": "turn_order", "config": {"players": [f"player-{i + 1}" for i in range(base["players"])]}}]
    return base
