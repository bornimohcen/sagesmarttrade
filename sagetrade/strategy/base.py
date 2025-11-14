from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from sagetrade.signals.aggregator import CompositeSignal


@dataclass
class Decision:
    """Proposed trading decision produced by a strategy.

    This is intentionally abstracted from any specific broker API.
    """

    symbol: str
    strategy_name: str
    side: str  # "buy" or "sell"
    size_pct: float  # fraction of account equity, e.g. 0.001 = 0.1%
    order_type: str  # "market" or "limit"
    limit_price: Optional[float]
    take_profit_pct: float  # +0.003 = +0.3% from entry
    stop_loss_pct: float  # -0.005 = -0.5% from entry
    target_duration_sec: int
    reason: str


class Strategy(Protocol):
    """Strategy interface for plugins.

    Strategies are expected to be stateless or light-state objects.
    State that must survive restarts should be stored elsewhere.
    """

    name: str

    def initialize(self, config: Dict[str, Any]) -> None:
        ...

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        """Receive a composite signal and decide whether to open a trade."""
        ...

    def on_tick(self, market_state: Dict[str, Any]) -> List[Decision]:
        """Optional: manage open positions or issue follow-up decisions."""
        return []

