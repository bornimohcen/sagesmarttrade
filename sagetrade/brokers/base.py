from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BrokerBase(ABC):
    """Abstract broker interface for paper and live brokers."""

    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """Return a normalized account summary.

        Expected keys:
        - balance: float
        - equity: float
        - realized_pnl: float
        - open_positions: int
        - open_notional: float
        - per_symbol_notional: dict[str, float]
        """

    # Concrete broker classes may expose richer methods (submit orders, etc.),
    # but for risk-state synchronization this summary contract is sufficient.


__all__ = ["BrokerBase"]

