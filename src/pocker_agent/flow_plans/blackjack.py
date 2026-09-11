"""Bounded point-game composition: every decision and mutation is a Tool call."""


def blackjack_plan(rules):
    nodes = {}

    def call(name, tool, operation, args, next_node, result=None):
        action = {"tool": tool, "operation": operation, "args": args}
        if result is not None:
            action["result_key"] = result
        nodes[name] = {"kind": "call", "action": action, "next": next_node}

    def state(name, values, next_node):
        call(name, "state", "update", {"state": "$state", "values": values}, next_node)

    def logic(name, expression, next_node, result="condition"):
        call(name, "logic", "evaluate", {"expression": expression}, next_node, result)

    def branch(name, yes, no, value="$state.condition"):
        nodes[name] = {"kind": "branch", "value": value,
                       "cases": [{"value": True, "target": yes}], "next": no}

    def rank(name, player, next_node):
        call(name, "hand_rank", "evaluate", {"cards": f"$state.hands.{player}"},
             next_node, "human_rank" if player == 0 else "dealer_rank")

    target = rules.target
    natural_human = {"all": [{"eq": ["$state.human_rank.total", target]},
                             {"eq": ["$state.human_size", 2]}]}
    natural_dealer = {"all": [{"eq": ["$state.dealer_rank.total", target]},
                              {"eq": ["$state.dealer_size", 2]}]}
    logic("round_seed", {"join": ["$state.seed", ":", "$state.round"]}, "prepare", "round_seed")
    state("prepare", {"hands": [[], []], "reveal": False, "phase": "要牌或停牌",
                      "round_winners": [], "feedback": ""}, "shuffle")
    call("shuffle", "deck", "shuffled", {"seed": "$state.round_seed"}, "deal", "stock")
    call("deal", "deck", "deal_into", {"stock": "$state.stock", "hands": "$state.hands",
                                          "cards_each": 2}, "initial_human")
    rank("initial_human", 0, "initial_dealer")
    rank("initial_dealer", 1, "initial_totals")
    state("initial_totals", {"totals": ["$state.human_rank.total", "$state.dealer_rank.total"]}, "initial_check")
    logic("initial_check", {"any": [{"eq": ["$state.human_rank.total", target]},
                                     {"eq": ["$state.dealer_rank.total", target]}]}, "initial_branch")
    branch("initial_branch", "settle_human", "wait")
    nodes["wait"] = {"kind": "wait", "inputs": {"hit": "hit", "stand": "settle_human"}}
    call("hit", "deck", "draw", {"stock": "$state.stock", "hand": "$state.hands.0"}, "hit_rank")
    rank("hit_rank", 0, "hit_totals")
    state("hit_totals", {"totals": ["$state.human_rank.total", "$state.dealer_rank.total"]}, "hit_check")
    logic("hit_check", {"ge": ["$state.human_rank.total", target]}, "hit_branch")
    branch("hit_branch", "settle_human", "wait")

    rank("settle_human", 0, "settle_dealer")
    rank("settle_dealer", 1, "human_size")
    logic("human_size", {"count": ["$state.hands.0"]}, "dealer_size", "human_size")
    logic("dealer_size", {"count": ["$state.hands.1"]}, "skip_draw", "dealer_size")
    logic("skip_draw", {"any": ["$state.human_rank.bust", natural_human, natural_dealer]}, "skip_branch")
    branch("skip_branch", "contest", "dealer_check")
    logic("dealer_check", {"any": [
        {"lt": ["$state.dealer_rank.total", rules.dealer_stand_on]},
        {"all": [{"eq": ["$state.dealer_rank.total", rules.dealer_stand_on]},
                 "$state.dealer_rank.soft", rules.dealer_hits_soft_17]}]}, "dealer_branch")
    branch("dealer_branch", "dealer_draw", "contest_size")
    call("dealer_draw", "deck", "draw", {"stock": "$state.stock", "hand": "$state.hands.1"}, "dealer_rank")
    rank("dealer_rank", 1, "dealer_check")
    logic("contest_size", {"count": ["$state.hands.1"]}, "contest", "dealer_size")
    call("contest", "point_contest", "resolve", {
        "totals": ["$state.human_rank.total", "$state.dealer_rank.total"],
        "sizes": ["$state.human_size", "$state.dealer_size"], "target": target,
        "first_bust_loses": True}, "award_check", "round_winners")
    logic("award_check", {"eq": [{"count": ["$state.round_winners"]}, 1]}, "award_branch")
    branch("award_branch", "award", "reveal")
    call("award", "score_settle", "call", {"scores": "$state.scores", "winners": "$state.round_winners",
                                               "points": 1}, "reveal", "scores")
    state("reveal", {"reveal": True, "phase": "本轮结算",
                     "totals": ["$state.human_rank.total", "$state.dealer_rank.total"]}, "round_limit")
    logic("round_limit", {"ge": ["$state.round", "$state.max_rounds"]}, "round_branch")
    branch("round_branch", "winners", "next_wait")
    nodes["next_wait"] = {"kind": "wait", "inputs": {"next_round": "next_round"}}
    logic("next_round", {"add": ["$state.round", 1]}, "round_seed", "round")
    call("winners", "winner_resolve", "call", {"values": "$state.scores"}, "finish", "winners")
    state("finish", {"finished": True, "finish_reason": "round_limit"}, "end")
    nodes["end"] = {"kind": "end"}
    return {"schema_version": "1.0", "game_kind": "blackjack", "players": 2,
            "tools": [{"name": "deck", "config": rules.deck.model_dump(mode="json")},
                      {"name": "hand_rank", "config": {"target": target}},
                      *[{"name": name} for name in ("state", "logic", "point_contest", "score_settle", "winner_resolve")]],
            "flow": {"entry": "round_seed", "initial": {"round": 1, "max_rounds": rules.max_rounds,
                "finished": False, "winners": [], "scores": [0, 0], "current_player": 0,
                "visible_counts": [2, 1], "labels": ["你", "庄家"]}, "nodes": nodes}}
