from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Sequence

import pandas as pd

from sagetrade.backtest.trade_log import BacktestTradeRecord, TradeLog
from sagetrade.brokers.backtest import BacktestBroker
from sagetrade.risk.manager import RiskManager
from sagetrade.signals.aggregator import build_composite_signal
from sagetrade.signals.nlp_news import compute_nlp_news_signals
from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.signals.social import compute_social_signals
from sagetrade.strategy.registry import StrategyManager
from sagetrade.utils.logging import log_event


def run_backtest(
    symbol: str,
    bars: Sequence[dict],
    news_items: Sequence[dict],
    initial_equity: float = 10_000.0,
    window: int = 20,
) -> TradeLog:
    """Simplified backtest runner for one symbol using existing components."""
    if not bars:
        raise ValueError("No bars provided for backtest.")

    # Sort bars by timestamp if present.
    bars_sorted = sorted(bars, key=lambda b: b.get("ts", 0.0))

    broker = BacktestBroker(initial_equity=initial_equity)
    risk = RiskManager()
    risk.state.equity = initial_equity
    risk.state.equity_start = initial_equity

    # Static NLP/social placeholders.
    nlp_sig = compute_nlp_news_signals("market")
    social_sig = compute_social_signals(symbol)

    strat_mgr = StrategyManager()
    trade_log = TradeLog()

    last_price = float(bars_sorted[-1]["c"])

    for bar in bars_sorted:
        price = float(bar["c"])
        ts = float(bar.get("ts", bar.get("timestamp", 0.0)))
        dt = datetime.utcfromtimestamp(ts)

        # Rolling window for quant signals
        # For simplicity reuse get_signals_from_bars on the rolling subset.
        # Keep last `window` bars.
        idx = bars_sorted.index(bar)
        window_bars = bars_sorted[max(0, idx - window + 1) : idx + 1]
        if len(window_bars) < window:
            continue

        q_sig = get_signals_from_bars(symbol, window_bars, window=window)
        comp = build_composite_signal(symbol, q_sig, nlp_sig, social_sig)

        strategies = strat_mgr.select_for_signal(comp)
        for strat in strategies:
            decision = strat.on_new_signal(comp)
            if decision is None:
                continue

            allowed, reason = risk.can_open(decision, price)
            if not allowed:
                log_event("bt_trade_blocked", reason=reason, symbol=symbol, strategy=strat.name)
                continue

            pos = broker.submit_market_order(
                symbol=symbol,
                side=decision.side,
                qty=decision.qty if hasattr(decision, "qty") else decision.size_pct * (risk.state.equity / price),
                price=price,
                ts=dt,
                strategy_name=strat.name,
            )
            risk.on_open(decision, price)

            # Evaluate TP/SL on next bar close (here simplified to immediate close at same bar).
            # For brevity, close at same bar price to log trades quickly.
            closed, notional = broker.close_position(symbol, price, dt)
            risk.on_close(closed.symbol, notional, closed.realized_pnl)

            trade_log.add_trade(
                BacktestTradeRecord(
                    trade_id=closed.id,
                    symbol=closed.symbol,
                    strategy_name=closed.strategy_name or strat.name,
                    side=closed.side,
                    qty=closed.qty,
                    entry_time=closed.opened_at,
                    exit_time=closed.closed_at or dt,
                    entry_price=closed.entry_price,
                    exit_price=price,
                    realized_pnl=closed.realized_pnl,
                )
            )

    # Close any remaining positions at last price
    for sym in list(broker._positions.keys()):
        pos, notional = broker.close_position(sym, last_price, datetime.utcfromtimestamp(float(bars_sorted[-1].get("ts", 0.0))))
        risk.on_close(pos.symbol, notional, pos.realized_pnl)
        trade_log.add_trade(
            BacktestTradeRecord(
                trade_id=pos.id,
                symbol=pos.symbol,
                strategy_name=pos.strategy_name or "unknown",
                side=pos.side,
                qty=pos.qty,
                entry_time=pos.opened_at,
                exit_time=pos.closed_at or datetime.utcnow(),
                entry_price=pos.entry_price,
                exit_price=last_price,
                realized_pnl=pos.realized_pnl,
            )
        )

    return trade_log


__all__ = ["run_backtest"]

