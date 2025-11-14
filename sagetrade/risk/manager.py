from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from sagetrade.strategy.base import Decision


@dataclass
class RiskConfig:
    initial_equity: float = 10_000.0
    max_open_trades: int = 20
    max_exposure_pct: float = 100.0  # total open notional as % of equity
    per_symbol_max_trades: int = 5
    max_trade_risk_pct: float = 0.5  # per-trade notional as % of equity
    max_daily_loss_pct: float = 3.0


@dataclass
class RiskState:
    equity_start: float
    equity: float
    realized_pnl: float = 0.0
    open_trades: int = 0
    open_notional_by_symbol: Dict[str, float] = field(default_factory=dict)


class RiskManager:
    """Simple risk manager for micro-trades.

    Tracks exposure and enforces basic limits before opening trades.
    """

    def __init__(self, cfg: RiskConfig | None = None) -> None:
        self.cfg = cfg or RiskConfig()
        self.state = RiskState(
            equity_start=self.cfg.initial_equity,
            equity=self.cfg.initial_equity,
        )

    def can_open(self, decision: Decision, price: float) -> Tuple[bool, str]:
        """Return whether a new trade can be opened under current limits."""
        if self.circuit_breaker_triggered():
            return False, "circuit_breaker_triggered"

        equity = self.state.equity
        if equity <= 0:
            return False, "equity_non_positive"

        notional = equity * decision.size_pct
        if notional <= 0:
            return False, "non_positive_notional"

        # Per-trade risk
        trade_risk_pct = (notional / equity) * 100.0
        if trade_risk_pct > self.cfg.max_trade_risk_pct:
            print(
                "[RISK-DEBUG] max_trade_risk_pct_exceeded "
                f"symbol={decision.symbol}, equity={equity:.4f}, "
                f"size_pct={decision.size_pct:.6f}, notional={notional:.4f}, "
                f"trade_risk_pct={trade_risk_pct:.4f}, "
                f"max_trade_risk_pct={self.cfg.max_trade_risk_pct:.4f}"
            )
            return False, "max_trade_risk_pct_exceeded"

        # Max number of open trades
        if self.state.open_trades + 1 > self.cfg.max_open_trades:
            return False, "max_open_trades_exceeded"

        # Per-symbol limit
        sym = decision.symbol
        sym_trades = sum(1 for s in self.state.open_notional_by_symbol if s == sym)
        if sym_trades + 1 > self.cfg.per_symbol_max_trades:
            return False, "per_symbol_max_trades_exceeded"

        # Exposure check
        new_open_notional = sum(self.state.open_notional_by_symbol.values()) + notional
        exposure_pct = (new_open_notional / equity) * 100.0
        if exposure_pct > self.cfg.max_exposure_pct:
            return False, "max_exposure_pct_exceeded"

        return True, "ok"

    def on_open(self, decision: Decision, price: float) -> None:
        equity = self.state.equity
        notional = equity * decision.size_pct
        self.state.open_trades += 1
        self.state.open_notional_by_symbol[decision.symbol] = (
            self.state.open_notional_by_symbol.get(decision.symbol, 0.0) + notional
        )

    def on_close(self, symbol: str, notional: float, pnl: float) -> None:
        self.state.open_trades = max(0, self.state.open_trades - 1)
        self.state.open_notional_by_symbol[symbol] = max(
            0.0,
            self.state.open_notional_by_symbol.get(symbol, 0.0) - notional,
        )
        self.state.realized_pnl += pnl
        self.state.equity = self.state.equity + pnl

    def circuit_breaker_triggered(self) -> bool:
        dd = self.drawdown_pct()
        return dd >= self.cfg.max_daily_loss_pct

    def drawdown_pct(self) -> float:
        if self.state.equity_start <= 0:
            return 0.0
        loss = self.state.equity_start - self.state.equity
        return max(0.0, (loss / self.state.equity_start) * 100.0)
