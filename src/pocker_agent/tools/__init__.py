"""Composable deterministic card-game tools.

Tools are deliberately small and side-effect free; a GameLayer owns orchestration.
"""
from .core import CardRef, DeckTool, ToolContext, ToolError, ToolResult
from .registry import ToolRegistry, default_registry
from .ranking import HandRankTool, best_of, five_card_rank
from .betting import PotTool
from .plan import ToolInvocation, ToolAction, ToolPlan
from .doudizhu import DoudizhuHand, beats, classify
from .plans import plan_for_rules
from .settlement import doudizhu_multiplier, doudizhu_scores
from .zones import ZoneTool
from .turns import TurnOrderTool
from .matching import matches, follow_suit, group_by
from .conditions import evaluate
from .patterns import resolve_trick, detect_meld
from .draw_discard import DrawDiscardTool
from .climbing import climb_beats
from .triggers import TriggerTool
from .holdem import BettingRoundTool, PhaseProgressTool, CommunityDealTool, AllInTool, showdown, settle_pots

__all__ = ["CardRef", "DeckTool", "ToolContext", "ToolError", "ToolResult", "ToolRegistry", "default_registry", "HandRankTool", "best_of", "five_card_rank", "PotTool", "ToolInvocation", "ToolAction", "ToolPlan", "DoudizhuHand", "beats", "classify", "plan_for_rules", "doudizhu_multiplier", "doudizhu_scores", "ZoneTool", "TurnOrderTool", "matches", "follow_suit", "group_by", "evaluate", "resolve_trick", "detect_meld", "DrawDiscardTool", "climb_beats", "TriggerTool", "BettingRoundTool", "PhaseProgressTool", "CommunityDealTool", "AllInTool", "showdown", "settle_pots"]
