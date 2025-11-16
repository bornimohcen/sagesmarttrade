from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple

from sagetrade.brokers import BrokerBase
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class BacktestPosition:
    id: str
    symbol: str
    side: str  # "long" or "short"
    qty: float
    entry_price: float
    opened_at: datetime
    closed_at: datetime | None = None
    realized_pnl: float = 0.0
    strategy_name: str | None = None
    meta: dict = field(default_factory=dict)


class BacktestBroker(BrokerBase):
    """Simplified broker for backtesting on historical bars."""

    def __init__(self, initial_equity: float) -> None:
        self._equity = initial_equity
        self._cash = initial_equity
        self._positions: Dict[str, BacktestPosition] = {}  # one position per symbol for simplicity

    # BrokerBase contract
    def get_account_summary(self) -> Dict[str, float]:
        per_symbol_notional: Dict[str, float] = {}
        for pos in self._positions.values():
            notional = pos.qty * pos.entry_price
            per_symbol_notional[pos.symbol] = per_symbol_notional.get(pos.symbol, 0.0) + notional
        open_notional = sum(per_symbol_notional.values())
        return {
            "balance": self._cash,
            "equity": self._equity,
            "realized_pnl": self._equity - self._cash,
            "open_positions": len(self._positions),
            "open_notional": open_notional,
            "per_symbol_notional": per_symbol_notional,
        }

    # Backtest-specific helpers
    def submit_market_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        ts: datetime,
        strategy_name: str | None = None,
    ) -> BacktestPosition:
        """Fill immediately at given price (no slippage)."""
        pos_side = "long" if side == "buy" else "short"
        pos_id = f"bt-{symbol}-{ts.timestamp()}"
        pos = BacktestPosition(
            id=pos_id,
            symbol=symbol,
            side=pos_side,
            qty=qty,
            entry_price=price,
            opened_at=ts,
            strategy_name=strategy_name,
        )
        self._positions[symbol] = pos
        notional = qty * price
        self._cash -= notional if pos_side == "long" else 0.0
        self._equity = self._cash  # unrealized handled on close only in this simple broker
        return pos

    def close_position(self, symbol: str, price: float, ts: datetime) -> Tuple[BacktestPosition, float]:
        if symbol not in self._positions:
            raise KeyError(f"No open position for symbol {symbol}")
        pos = self._positions.pop(symbol)
        notional = pos.qty * pos.entry_price
        if pos.side == "long":
            pnl = (price - pos.entry_price) * pos.qty
        else:
            pnl = (pos.entry_price - price) * pos.qty
        pos.closed_at = ts
        pos.realized_pnl = pnl
        self._cash += notional + pnl if pos.side == "long" else self._cash + pnl
        self._equity = self._cash
        return pos, notional


__all__ = ["BacktestBroker", "BacktestPosition"]

