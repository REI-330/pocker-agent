"""Composable deterministic card-game tools.

Tools are deliberately small and side-effect free; a GameLayer owns orchestration.
"""
from pocker_agent.game_runtime.tools.core import CardRef, DeckTool, ToolContext, ToolError, ToolResult
from pocker_agent.game_runtime.tools.registry import ToolRegistry, default_registry
from pocker_agent.game_runtime.tools.ranking import HandRankTool, best_of, five_card_rank
from pocker_agent.game_runtime.tools.betting import PotTool
from pocker_agent.game_runtime.tools.plan import ToolInvocation, ToolAction, ToolPlan
from pocker_agent.game_runtime.tools.doudizhu import DoudizhuHand, beats, classify
from pocker_agent.game_runtime.tools.plans import plan_for_rules
from pocker_agent.game_runtime.tools.settlement import doudizhu_multiplier, doudizhu_scores
from pocker_agent.game_runtime.tools.zones import ZoneTool
from pocker_agent.game_runtime.tools.turns import TurnOrderTool
from pocker_agent.game_runtime.tools.matching import matches, follow_suit, group_by
from pocker_agent.game_runtime.tools.conditions import evaluate
from pocker_agent.game_runtime.tools.patterns import resolve_trick, detect_meld
from pocker_agent.game_runtime.tools.draw_discard import DrawDiscardTool
from pocker_agent.game_runtime.tools.climbing import climb_beats
from pocker_agent.game_runtime.tools.triggers import TriggerTool
from pocker_agent.game_runtime.tools.holdem import BettingRoundTool, PhaseProgressTool, CommunityDealTool, AllInTool, showdown, settle_pots

__all__ = ["CardRef", "DeckTool", "ToolContext", "ToolError", "ToolResult", "ToolRegistry", "default_registry", "HandRankTool", "best_of", "five_card_rank", "PotTool", "ToolInvocation", "ToolAction", "ToolPlan", "DoudizhuHand", "beats", "classify", "plan_for_rules", "doudizhu_multiplier", "doudizhu_scores", "ZoneTool", "TurnOrderTool", "matches", "follow_suit", "group_by", "evaluate", "resolve_trick", "detect_meld", "DrawDiscardTool", "climb_beats", "TriggerTool", "BettingRoundTool", "PhaseProgressTool", "CommunityDealTool", "AllInTool", "showdown", "settle_pots"]
