"""Backtesting utilities for SAGE SMART TRADE."""

from .trade_log import BacktestTradeRecord, TradeLog
from .report import compute_equity_curve, compute_metrics, summarize_by_strategy, summarize_by_symbol

__all__ = [
    "BacktestTradeRecord",
    "TradeLog",
    "compute_equity_curve",
    "compute_metrics",
    "summarize_by_strategy",
    "summarize_by_symbol",
]

