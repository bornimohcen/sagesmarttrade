from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


def _now_ts() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@dataclass
class Order:
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    qty: float
    type: str  # "market" or "limit"
    status: str  # "created", "filled", "partial", "cancelled"
    created_at: float
    updated_at: float
    limit_price: Optional[float] = None
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    cancelled_reason: Optional[str] = None


@dataclass
class Position:
    id: str
    symbol: str
    side: str  # "long" or "short"
    qty: float
    entry_price: float
    take_profit: Optional[float]
    stop_loss: Optional[float]
    opened_at: float
    closed_at: Optional[float] = None
    realized_pnl: float = 0.0


@dataclass
class AccountState:
    balance: float
    equity: float
    realized_pnl: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)


def create_market_order(symbol: str, side: str, qty: float, limit_price: Optional[float] = None) -> Order:
    now = _now_ts()
    return Order(
        id=_new_id("ord"),
        symbol=symbol,
        side=side,
        qty=qty,
        type="market",
        status="created",
        created_at=now,
        updated_at=now,
        limit_price=limit_price,
    )


