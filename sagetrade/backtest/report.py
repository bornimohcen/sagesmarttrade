from __future__ import annotations

import math
from typing import Dict, List, Sequence

import pandas as pd

from sagetrade.backtest.trade_log import BacktestTradeRecord


def compute_equity_curve(trades: Sequence[BacktestTradeRecord], start_equity: float) -> pd.DataFrame:
    equity = start_equity
    rows = []
    for t in trades:
        equity += t.realized_pnl
        rows.append({"timestamp": t.exit_time, "equity": equity})
    return pd.DataFrame(rows)


def compute_metrics(trades: Sequence[BacktestTradeRecord], start_equity: float) -> Dict[str, float]:
    if not trades:
        return {"total_pnl": 0.0, "return_pct": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "sharpe": 0.0}

    equity_curve = compute_equity_curve(trades, start_equity)
    total_pnl = equity_curve.iloc[-1]["equity"] - start_equity
    return_pct = (total_pnl / start_equity * 100.0) if start_equity > 0 else 0.0

    # Max drawdown
    max_eq = -math.inf
    max_dd = 0.0
    for eq in equity_curve["equity"]:
        if eq > max_eq:
            max_eq = eq
        dd = (max_eq - eq) / max_eq if max_eq > 0 else 0.0
        max_dd = max(max_dd, dd)

    # Win rate
    wins = sum(1 for t in trades if t.realized_pnl > 0)
    win_rate = wins / len(trades) * 100.0

    # Sharpe (very rough, step-based)
    sharpe = 0.0
    if len(equity_curve) > 1:
        rets = equity_curve["equity"].pct_change().dropna()
        if not rets.empty and rets.std() > 0:
            sharpe = (rets.mean() / rets.std()) * math.sqrt(len(rets))

    return {
        "total_pnl": total_pnl,
        "return_pct": return_pct,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "sharpe": sharpe,
    }


def summarize_by_strategy(trades: Sequence[BacktestTradeRecord]) -> pd.DataFrame:
    df = pd.DataFrame([t.__dict__ for t in trades])
    if df.empty:
        return df
    return df.groupby("strategy_name")["realized_pnl"].agg(["count", "sum", "mean"])


def summarize_by_symbol(trades: Sequence[BacktestTradeRecord]) -> pd.DataFrame:
    df = pd.DataFrame([t.__dict__ for t in trades])
    if df.empty:
        return df
    return df.groupby("symbol")["realized_pnl"].agg(["count", "sum", "mean"])


__all__ = ["compute_equity_curve", "compute_metrics", "summarize_by_strategy", "summarize_by_symbol"]

