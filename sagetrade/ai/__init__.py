"""AI helpers for signals, risk inspection, and trade explanations.

This package starts as lightweight scaffolding; concrete integrations with
LLM providers can be added incrementally as the project matures.
"""

from .models import AISignalAdvice, AITradeExplanation, AITradeReview
from .client import build_llm_client
from .signal_advisor import AISignalAdvisor
from .trade_explainer import (
    explain_before_trade,
    explain_after_trade,
    explain_open_trade_ai,
    explain_closed_trade_ai,
)

__all__ = [
    "AISignalAdvice",
    "AITradeExplanation",
    "AITradeReview",
    "build_llm_client",
    "AISignalAdvisor",
    "explain_before_trade",
    "explain_after_trade",
    "explain_open_trade_ai",
    "explain_closed_trade_ai",
]

