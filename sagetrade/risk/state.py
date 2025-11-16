from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict
import time


@dataclass
class RiskState:
    """In-memory snapshot of account risk state.

    This is the single source of truth inside the engine about current equity,
    realized PnL, and symbol-level exposure for the current session.
    """

    equity_start: float
    equity: float
    realized_pnl: float = 0.0
    open_trades: int = 0
    open_notional_by_symbol: Dict[str, float] = field(default_factory=dict)
    last_equity_update_ts: float = field(default_factory=lambda: time.time())
    session_start_ts: float = field(default_factory=lambda: time.time())

    @property
    def daily_pnl(self) -> float:
        return self.equity - self.equity_start

    @property
    def total_open_notional(self) -> float:
        return sum(self.open_notional_by_symbol.values())


__all__ = ["RiskState"]

