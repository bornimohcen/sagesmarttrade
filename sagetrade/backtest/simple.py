from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from sagetrade.execution.paper_broker import PaperBroker
from sagetrade.risk.manager import RiskManager
from sagetrade.signals.aggregator import aggregate
from sagetrade.signals.nlp import get_signals as get_nlp_signals
from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.strategy.registry import StrategyManager
from sagetrade.utils.logging import log_event
from sagetrade.utils.metrics import get_registry


@dataclass
class TradeLog:
    position_id: str
    symbol: str
    side: str
    qty: float
    entry_price: float
    exit_price: float
    opened_at: float
    closed_at: float
    pnl: float
    strategy_name: str


@dataclass
class BacktestResult:
    symbol: str
    equity_curve: List[Tuple[float, float]]  # (ts, equity)
    trades: List[TradeLog] = field(default_factory=list)

    @property
    def total_pnl(self) -> float:
        if not self.equity_curve:
            return 0.0
        start_equity = self.equity_curve[0][1]
        end_equity = self.equity_curve[-1][1]
        return end_equity - start_equity

    @property
    def max_drawdown(self) -> float:
        peak = -math.inf
        max_dd = 0.0
        for _, eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def return_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        start_equity = self.equity_curve[0][1]
        if start_equity <= 0:
            return 0.0
        return self.total_pnl / start_equity * 100.0

    @property
    def sharpe(self) -> float:
        """Simple Sharpe approximation based on per-step returns.

        This is intentionally basic and intended for relative comparison between experiments.
        """
        if len(self.equity_curve) < 3:
            return 0.0
        rets: List[float] = []
        prev_eq = self.equity_curve[0][1]
        for _, eq in self.equity_curve[1:]:
            if prev_eq > 0:
                rets.append((eq - prev_eq) / prev_eq)
            prev_eq = eq
        if not rets:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
        if var <= 0:
            return 0.0
        std = math.sqrt(var)
        # Not annualized; scaled by sqrt(N) for comparability.
        return (mean / std) * math.sqrt(len(rets))


def run_single_symbol_backtest(
    symbol: str,
    bars: Sequence[dict],
    news_items: Sequence[dict],
    window: int = 20,
) -> BacktestResult:
    """Run a simple backtest over all bars for one symbol.

    - Uses fixed NLP signals over the whole period (from news_items).
    - On each bar (after warm-up window), computes quant + composite signals.
    - Feeds signals into StrategyManager -> RiskManager -> PaperBroker.
    - Closes positions when TP/SL hit on bar close.
    """
    if not bars:
        raise ValueError("No market bars provided.")

    registry = get_registry()
    registry.counter("backtest_runs_total", "Total number of single-symbol backtests run").inc()
    log_event(
        "backtest_run_started",
        symbol=symbol,
        bars=len(bars),
        window=window,
    )

    # Sort by timestamp if available.
    bars_sorted = sorted(bars, key=lambda b: b.get("ts", 0.0))

    nlp_sig = get_nlp_signals("market", news_items)
    manager = StrategyManager()
    risk = RiskManager()
    broker = PaperBroker(initial_balance=risk.cfg.initial_equity, account_id=f"backtest-{symbol}")

    equity_curve: List[Tuple[float, float]] = []
    trades: List[TradeLog] = []

    window_bars: List[dict] = []
    last_ts: float = 0.0
    last_price: float = float(bars_sorted[-1]["c"])

    for bar in bars_sorted:
        window_bars.append(bar)
        if len(window_bars) < window:
            continue
        if len(window_bars) > window:
            window_bars.pop(0)

        price = float(bar["c"])
        ts = float(bar.get("ts", 0.0))
        last_ts = ts or last_ts
        last_price = price

        q_sig = get_signals_from_bars(symbol, window_bars, window=window)
        comp = aggregate(symbol, q_sig, nlp_sig)

        strategies = manager.select_for_signal(comp)
        for strat in strategies:
            decision = strat.on_new_signal(comp)
            if decision is None:
                continue

            allowed, reason = risk.can_open(decision, price)
            if not allowed:
                continue

            order, position = broker.execute_decision(decision, price)
            risk.on_open(decision, price)

        # Evaluate TP/SL on this bar's close.
        closed = broker.check_tp_sl({symbol: price})
        for pos_id, (pos, notional) in closed.items():
            # Risk manager update.
            risk.on_close(pos.symbol, notional, pos.realized_pnl)

            trades.append(
                TradeLog(
                    position_id=pos_id,
                    symbol=pos.symbol,
                    side=pos.side,
                    qty=pos.qty,
                    entry_price=pos.entry_price,
                    exit_price=price,
                    opened_at=pos.opened_at,
                    closed_at=pos.closed_at or ts,
                    pnl=pos.realized_pnl,
                    strategy_name="",  # can be filled if we propagate strategy name into Position later.
                )
            )

        equity_curve.append((ts, risk.state.equity))

    # At the end of the period, force-close any remaining open positions at last_price.
    if broker.account.positions:
        for pos_id, pos in list(broker.account.positions.items()):
            closed, notional = broker.close_position(pos_id, last_price)
            risk.on_close(closed.symbol, notional, closed.realized_pnl)
            trades.append(
                TradeLog(
                    position_id=pos_id,
                    symbol=closed.symbol,
                    side=closed.side,
                    qty=closed.qty,
                    entry_price=closed.entry_price,
                    exit_price=last_price,
                    opened_at=closed.opened_at,
                    closed_at=closed.closed_at or last_ts,
                    pnl=closed.realized_pnl,
                    strategy_name="",
                )
            )
        equity_curve.append((last_ts, risk.state.equity))

    result = BacktestResult(symbol=symbol, equity_curve=equity_curve, trades=trades)

    # Update basic metrics for observability.
    registry.gauge("backtest_last_trades", "Number of trades in the last backtest").set(float(len(trades)))
    registry.gauge("backtest_last_total_pnl", "Total PnL of the last backtest").set(result.total_pnl)
    registry.gauge("backtest_last_return_pct", "Return pct of the last backtest").set(result.return_pct)
    registry.gauge("backtest_last_max_drawdown", "Max drawdown of the last backtest").set(result.max_drawdown)

    log_event(
        "backtest_run_finished",
        symbol=symbol,
        trades=len(trades),
        total_pnl=result.total_pnl,
        return_pct=result.return_pct,
        max_drawdown=result.max_drawdown,
    )

    return result
