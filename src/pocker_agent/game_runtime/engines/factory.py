"""Single dispatch boundary shared by HTTP runtime and deterministic simulation."""
from copy import deepcopy

from pocker_agent.game_runtime.engines.legacy import RuleEngine
from pocker_agent.game_runtime.engines.families import ArithmeticEngine, BlackjackEngine, SheddingEngine, restore_state
from pocker_agent.domain.rules import parse_rule
from pocker_agent.game_runtime.plugins.engine import PluginEngine
from pocker_agent.game_runtime.engines.doudizhu import DoudizhuEngine
from pocker_agent.game_runtime.engines.holdem import HoldemEngine

FAMILIES = {"arithmetic": ArithmeticEngine, "blackjack": BlackjackEngine, "shedding": SheddingEngine, "doudizhu": DoudizhuEngine, "holdem": HoldemEngine, "plugin": PluginEngine}


def create_engine(rules, seed=0, player_count=None, tool_plan=None):
    factory = FAMILIES.get(getattr(rules, "kind", None), RuleEngine)
    if getattr(rules, "kind", None) in {"arithmetic", "blackjack", "shedding", "doudizhu", "holdem"}:
        return factory(rules, seed=seed, player_count=player_count, tool_plan=tool_plan)
    return factory(rules, seed=seed, player_count=player_count)


def restore_engine(data):
    # Runtime uses restoration as a transaction copy. Events and nested state
    # must not alias the source when a later action or bot step is rejected.
    data = deepcopy(data)
    rules = parse_rule(data["rules"])
    if getattr(rules, "kind", None) == "doudizhu":
        from pocker_agent.game_runtime.engines.doudizhu import DoudizhuState
        from pocker_agent.game_runtime.tools import CardRef
        engine = create_engine(rules, seed=data["seed"], tool_plan=data.get("tool_plan"))
        s = data["state"]
        to_card = lambda c: CardRef(c["id"], c["rank"], c["suit"], c["value"])
        from pocker_agent.game_runtime.tools import DoudizhuHand
        lp = s.get("last_play")
        last_play = None if lp is None else DoudizhuHand(lp["kind"], lp["rank"], lp.get("length", 1), lp.get("wing", ""))
        engine.state = DoudizhuState([[to_card(c) for c in h] for h in s["hands"]], [to_card(c) for c in s["kitty"]],
                                     s["current_player"], s.get("landlord"), s.get("bid", 0), last_play,
                                     s.get("last_player"), s.get("passes", 0),
                                     finished=s.get("finished", False), winners=s.get("winners"), scores=s.get("scores"))
        engine.state.bombs=s.get("bombs",0); engine.state.landlord_plays=s.get("landlord_plays",0); engine.state.farmer_plays=s.get("farmer_plays",0)
        engine.events = data.get("events", [])
        return engine
    if getattr(rules, "kind", None) == "holdem":
        from pocker_agent.game_runtime.engines.holdem import HoldemState
        from pocker_agent.game_runtime.tools import CardRef
        engine = create_engine(rules, seed=data["seed"], tool_plan=data.get("tool_plan")); s = data["state"]
        cv=lambda c: CardRef(c["id"],c["rank"],c["suit"],c["value"])
        engine.state = HoldemState([[cv(c) for c in h] for h in s["hands"]],[cv(c) for c in s["deck"]],[cv(c) for c in s["board"]],s["stacks"],s["committed"],s.get("hand_committed", s["committed"]),set(s["folded"]),s["current_player"],s["street"],s["finished"],s.get("winners"),set(s.get("acted", [])),s.get("last_raise", 0))
        engine.events=data.get("events",[]); return engine
    if not hasattr(rules, "kind"): return RuleEngine.restore(data)
    engine = create_engine(rules, seed=data["seed"], tool_plan=data.get("tool_plan"))
    engine.state = restore_state(data["state"])
    engine.events, engine.extra = data["events"], dict(data["extra"])
    from pocker_agent.game_runtime.engines.legacy import Card
    engine.discard = [Card(**c) for c in data["discard"]]
    return engine
