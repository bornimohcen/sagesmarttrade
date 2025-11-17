from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from sagetrade.brokers import BrokerBase
from sagetrade.risk.state import RiskState
from sagetrade.utils.config import get_settings
from sagetrade.strategy.base import Decision
from sagetrade.utils.logging import get_logger


@dataclass
class RiskConfig:
    initial_equity: float = 10_000.0
    max_open_trades: int = 20
    max_exposure_pct: float = 100.0  # total open notional as % of equity
    per_symbol_max_trades: int = 5
    max_trade_risk_pct: float = 0.5  # per-trade notional as % of equity
    max_daily_loss_pct: float = 3.0


@dataclass
class RiskManager:
    """Simple risk manager for micro-trades.

    Tracks exposure and enforces basic limits before opening trades.
    """

    def __init__(
        self,
        cfg: RiskConfig | None = None,
        broker: Optional[BrokerBase] = None,
        state: Optional[RiskState] = None,
    ) -> None:
        if cfg is None:
            settings = get_settings()
            rs = settings.risk
            pb = settings.brokers.paper
            cfg = RiskConfig(
                initial_equity=pb.starting_equity,
                max_open_trades=rs.max_open_trades,
                # Config stores fractions (0.005 -> 0.5%), RiskConfig uses percentages.
                max_exposure_pct=rs.max_symbol_exposure_pct * 100.0,
                per_symbol_max_trades=RiskConfig.per_symbol_max_trades,
                max_trade_risk_pct=rs.max_risk_per_trade_pct * 100.0,
                max_daily_loss_pct=rs.max_daily_loss_pct * 100.0,
            )
        self.cfg = cfg
        self.state = state or RiskState(
            equity_start=self.cfg.initial_equity,
            equity=self.cfg.initial_equity,
        )
        self._broker = broker
        self._logger = get_logger(__name__)

    def attach_broker(self, broker: BrokerBase) -> None:
        """Attach a broker after construction (optional helper)."""
        self._broker = broker

    def refresh_from_broker(self) -> None:
        """Refresh RiskState from the attached broker account summary."""
        if self._broker is None:
            return
        summary = self._broker.get_account_summary()
        equity = float(summary.get("equity", self.state.equity))
        realized_pnl = float(summary.get("realized_pnl", self.state.realized_pnl))
        open_positions = int(summary.get("open_positions", self.state.open_trades))
        per_symbol_notional = dict(summary.get("per_symbol_notional", {}))

        self.state.equity = equity
        self.state.realized_pnl = realized_pnl
        self.state.open_trades = open_positions
        self.state.open_notional_by_symbol = per_symbol_notional

        from time import time as _time

        self.state.last_equity_update_ts = _time()

        self._logger.debug(
            "risk_state_updated event=risk_state_updated equity=%.2f realized_pnl=%.2f "
            "open_trades=%d total_open_notional=%.2f",
            self.state.equity,
            self.state.realized_pnl,
            self.state.open_trades,
            self.state.total_open_notional,
        )

    def can_open(self, decision: Decision, price: float) -> Tuple[bool, str]:
        """Return whether a new trade can be opened under current limits."""
        if self.circuit_breaker_triggered():
            reason = "circuit_breaker_triggered"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s equity=%.4f",
                decision.symbol,
                reason,
                self.state.equity,
            )
            return False, reason

        # Block equity shorts on accounts that are long-only (e.g., Alpaca paper cash).
        if decision.symbol.isalpha() and len(decision.symbol) <= 5 and decision.side == "sell":
            reason = "short_equities_not_allowed"
            self._logger.info(
                "trade_blocked event=trade_blocked symbol=%s reason=%s side=%s",
                decision.symbol,
                reason,
                decision.side,
            )
            return False, reason

        equity = self.state.equity
        if equity <= 0:
            reason = "equity_non_positive"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s equity=%.4f",
                decision.symbol,
                reason,
                equity,
            )
            return False, reason

        notional = equity * decision.size_pct
        if notional <= 0:
            reason = "non_positive_notional"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s equity=%.4f size_pct=%.6f",
                decision.symbol,
                reason,
                equity,
                decision.size_pct,
            )
            return False, reason

        # Per-trade risk
        trade_risk_pct = (notional / equity) * 100.0
        if trade_risk_pct > self.cfg.max_trade_risk_pct:
            reason = "max_trade_risk_pct_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s equity=%.4f "
                "size_pct=%.6f notional=%.4f trade_risk_pct=%.4f max_trade_risk_pct=%.4f",
                decision.symbol,
                reason,
                equity,
                decision.size_pct,
                notional,
                trade_risk_pct,
                self.cfg.max_trade_risk_pct,
            )
            return False, reason

        # Max number of open trades
        if self.state.open_trades + 1 > self.cfg.max_open_trades:
            reason = "max_open_trades_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s open_trades=%d max_open_trades=%d",
                decision.symbol,
                reason,
                self.state.open_trades,
                self.cfg.max_open_trades,
            )
            return False, reason

        # Per-symbol limit
        sym = decision.symbol
        sym_trades = sum(1 for s in self.state.open_notional_by_symbol if s == sym)
        if sym_trades + 1 > self.cfg.per_symbol_max_trades:
            reason = "per_symbol_max_trades_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s current_trades=%d max_per_symbol=%d",
                sym,
                reason,
                sym_trades,
                self.cfg.per_symbol_max_trades,
            )
            return False, reason

        # Exposure check
        new_open_notional = sum(self.state.open_notional_by_symbol.values()) + notional
        exposure_pct = (new_open_notional / equity) * 100.0
        if exposure_pct > self.cfg.max_exposure_pct:
            reason = "max_exposure_pct_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s exposure_pct=%.4f max_exposure_pct=%.4f",
                decision.symbol,
                reason,
                exposure_pct,
                self.cfg.max_exposure_pct,
            )
            return False, reason

        return True, "ok"

    def can_open_trade(self, symbol: str, notional: float) -> Tuple[bool, str]:
        """Risk gate based on symbol/notional and config fractions."""
        settings = get_settings()
        rs_cfg = settings.risk

        equity = max(self.state.equity, 0.0)
        max_trade_risk = rs_cfg.max_risk_per_trade_pct * equity
        current_symbol_notional = self.state.open_notional_by_symbol.get(symbol, 0.0)
        max_symbol_exposure = rs_cfg.max_symbol_exposure_pct * equity
        max_daily_loss = rs_cfg.max_daily_loss_pct * self.state.equity_start

        # 1) Daily loss check.
        if self.state.daily_pnl <= -max_daily_loss:
            reason = "max_daily_loss_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s daily_pnl=%.2f limit=%.2f",
                symbol,
                reason,
                self.state.daily_pnl,
                -max_daily_loss,
            )
            return False, reason

        # 2) Per-trade risk (approximate).
        if notional > max_trade_risk:
            reason = "max_trade_risk_pct_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s notional=%.2f max_trade_risk=%.2f",
                symbol,
                reason,
                notional,
                max_trade_risk,
            )
            return False, reason

        # 3) Per-symbol exposure.
        new_symbol_exposure = current_symbol_notional + notional
        if new_symbol_exposure > max_symbol_exposure:
            reason = "max_symbol_exposure_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s new_symbol_exposure=%.2f "
                "max_symbol_exposure=%.2f",
                symbol,
                reason,
                new_symbol_exposure,
                max_symbol_exposure,
            )
            return False, reason

        # 4) Max open trades.
        if self.state.open_trades >= rs_cfg.max_open_trades:
            reason = "max_open_trades_exceeded"
            self._logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s open_trades=%d max_open_trades=%d",
                symbol,
                reason,
                self.state.open_trades,
                rs_cfg.max_open_trades,
            )
            return False, reason

        return True, ""

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
