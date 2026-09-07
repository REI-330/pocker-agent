"""Independent acceptance oracle. Not imported by the game or code generator."""

import argparse
import json
from collections import Counter
from pathlib import Path

from pocker_agent.plugin_sandbox import shuffled_deck, simulate_plugin
from pocker_agent.plugin_schema import PluginRule, card_catalog


def verify(rule, same_color=False):
    catalog = card_catalog(rule)
    assert len(catalog) == 51 and "QS" not in catalog, "Must use all 51 requested cards"
    assert rule.players.min_players == rule.players.max_players == 2

    def key(id):
        c = catalog[id]
        return (c["rank"], c["suit"] in {"H", "D"}) if same_color else c["rank"]

    def remaining_counts(hand):
        return Counter({k: n % 2 for k, n in Counter(map(key, hand)).items() if n % 2})

    def counts(hand):
        return Counter(map(key, hand))

    results = []
    for seed in (2, 11, 41, 89, 133):
        trace = simulate_plugin(rule, seed)
        before = trace[0]["state"]
        deck = shuffled_deck(rule, seed)
        # Deal order can consume from either end, but distribution must be round-robin.
        expected = [
            [remaining_counts(deck[i::2]) for i in (0, 1)],
            [remaining_counts(deck[::-1][i::2]) for i in (0, 1)],
        ]
        assert [counts(h) for h in before["hands"]] in expected, (
            "Incorrect initial deal/pair removal"
        )
        if not before["finished"]:
            assert before["current_player"] == 0
        for index, frame in enumerate(trace[1:]):
            after, action = frame["state"], frame["action"]
            player = before["current_player"]
            target = 1 - player
            assert action["target_player"] == target, (
                f"seed {seed} move {index}: wrong target"
            )
            card = before["hands"][target][action["card_index"]]
            expected_hand = remaining_counts(before["hands"][player] + [card])
            assert counts(after["hands"][player]) == expected_hand, (
                f"seed {seed} move {index}: pair rule changed"
            )
            assert Counter(after["hands"][target]) == Counter(
                before["hands"][target]
            ) - Counter([card]), "Target must lose exactly selected card"
            assert not after["deck"], "No extra stock in old maid"
            if not after["finished"]:
                assert all(after["hands"]), (
                    "Empty player should exit/end two-player game"
                )
                assert after["current_player"] == target, "Players must alternate"
            before = after
        final = trace[-1]["state"]
        remaining = [(i, c) for i, h in enumerate(final["hands"]) for c in h]
        assert len(remaining) == 1 and catalog[remaining[0][1]]["rank"] == "Q", (
            "Exactly one queen must remain"
        )
        assert final["winners"] == [1 - remaining[0][0]], "Queen holder must lose"
        results.append(
            {"seed": seed, "moves": len(trace) - 1, "winner": final["winners"][0]}
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--same-color", action="store_true")
    args = parser.parse_args()
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    result = verify(PluginRule.model_validate(data["rules"]), args.same_color)
    print(json.dumps(result, ensure_ascii=False, indent=2))
