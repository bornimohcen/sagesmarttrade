from __future__ import annotations

from typing import Any, Dict

from sagetrade.signals.aggregator import CompositeSignal


def explain_before_trade(symbol: str, signal: CompositeSignal) -> str:
    """Return a human-readable pre-trade explanation.

    This is a placeholder meant to be replaced by an AI-powered explanation
    later. Keeping it simple for now helps wire the plumbing early.
    """
    return (
        f"Pre-trade explanation for {symbol}: "
        f"direction={signal.direction}, score={signal.score:.4f}, confidence={signal.confidence:.2f}."
    )


def explain_after_trade(symbol: str, trade_summary: Dict[str, Any]) -> str:
    """Return a human-readable post-trade explanation placeholder."""
    pnl = trade_summary.get("pnl")
    pnl_str = f"{pnl:.2f}" if isinstance(pnl, (int, float)) else str(pnl)
    return f"Post-trade summary for {symbol}: PnL={pnl_str}. Detailed AI review not implemented yet."


__all__ = ["explain_before_trade", "explain_after_trade"]

