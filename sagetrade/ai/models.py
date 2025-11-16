from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

AISignalDecision = Literal["approve", "caution", "reject"]


@dataclass
class AISignalAdvice:
    symbol: str
    strategy_name: str
    decision: AISignalDecision
    reason: str
    suggested_direction: Optional[str] = None  # "long" | "short" | "flat"
    suggested_confidence: Optional[float] = None  # 0..1


@dataclass
class AITradeExplanation:
    symbol: str
    strategy_name: str
    title: str  # short title
    summary: str  # main explanation text
    risks: List[str]
    notes: List[str]


@dataclass
class AITradeReview:
    symbol: str
    strategy_name: str
    outcome: str  # "win" | "loss" | "breakeven"
    pnl: float
    lesson: str
    improvements: List[str]


__all__ = ["AISignalAdvice", "AISignalDecision", "AITradeExplanation", "AITradeReview"]

