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
from .settlement import doudizhu_multiplier, doudizhu_scores, resolve_winners, settle_scores, DoudizhuSettlementTool
from .state_ops import StateTool, LogicTool, PointContestTool, DealerPolicyTool, ArithmeticDealTool, SheddingTurnTool
from .zones import ZoneTool
from .turns import TurnOrderTool
from .matching import matches, follow_suit, group_by
from .conditions import evaluate
from .patterns import resolve_trick, detect_meld
from .draw_discard import DrawDiscardTool
from .climbing import climb_beats
from .triggers import TriggerTool
from .holdem import BettingRoundTool, PhaseProgressTool, CommunityDealTool, AllInTool, showdown, settle_pots
from .gameflow import WinConditionTool, SettlementTool

__all__ = [name for name in globals() if not name.startswith("_")]
