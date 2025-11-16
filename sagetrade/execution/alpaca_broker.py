from __future__ import annotations

import os
from typing import Dict, Tuple

import requests

from sagetrade.brokers import BrokerBase
from sagetrade.execution.models import Order, Position, create_market_order
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


class AlpacaBroker(BrokerBase):
    """Minimal live/paper broker for Alpaca orders.

    Notes:
    - Uses market orders only (no TP/SL handling here).
    - check_tp_sl is a no-op; positions stay open until manually closed or via API.
    - Expects ALPACA_API_KEY / ALPACA_API_SECRET in environment.
    - base_url should be the paper/live trading endpoint (e.g., https://paper-api.alpaca.markets/v2).
    """

    def __init__(self, base_url: str) -> None:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/v2"):
            normalized = f"{normalized}/v2"
        self.base_url = normalized
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("ALPACA_API_KEY/ALPACA_API_SECRET not set in environment.")

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    def submit_order(self, order: Order) -> Order:
        payload = {
            "symbol": order.symbol,
            "qty": order.qty,
            "side": order.side,
            "type": "market",
            "time_in_force": "gtc",
        }
        resp = requests.post(f"{self.base_url}/orders", json=payload, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        order.id = data.get("id", order.id)
        order.status = data.get("status", "submitted")
        order.avg_fill_price = float(data.get("filled_avg_price") or order.avg_fill_price or 0.0)
        return order

    def cancel_order(self, order_id: str) -> None:
        resp = requests.delete(f"{self.base_url}/orders/{order_id}", headers=self._headers(), timeout=10)
        resp.raise_for_status()

    def get_positions(self) -> Dict[str, Position]:
        resp = requests.get(f"{self.base_url}/positions", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        positions: Dict[str, Position] = {}
        for p in resp.json():
            symbol = p["symbol"]
            qty = float(p["qty"])
            side = "long" if float(p.get("market_value", 0)) >= 0 else "short"
            positions[symbol] = Position(
                id=p.get("asset_id", symbol),
                symbol=symbol,
                side=side,
                qty=abs(qty),
                entry_price=float(p.get("avg_entry_price", 0.0)),
                take_profit=None,
                stop_loss=None,
            )
        return positions

    def get_account_summary(self) -> Dict[str, float]:
        resp = requests.get(f"{self.base_url}/account", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        acc = resp.json()
        equity = float(acc.get("equity", 0.0))
        cash = float(acc.get("cash", 0.0))
        return {
            "balance": cash,
            "equity": equity,
            "realized_pnl": float(acc.get("last_equity", equity)) - cash,
            "open_positions": 0,  # filled below if needed
            "open_notional": 0.0,
            "per_symbol_notional": {},
        }

    # Compatibility with paper_trade_loop expectations
    def execute_decision(self, decision, price: float) -> Tuple[Order, Position]:
        qty = decision.size_pct * (self.get_account_summary()["equity"] / max(price, 1e-8))
        order = create_market_order(decision.symbol, decision.side, qty)
        order = self.submit_order(order)
        position = Position(
            id=order.id.replace("ord", "pos"),
            symbol=decision.symbol,
            side="long" if decision.side == "buy" else "short",
            qty=qty,
            entry_price=price,
            take_profit=None,
            stop_loss=None,
            opened_at=order.created_at,
        )
        return order, position

    def summary(self) -> dict:
        return self.get_account_summary()

    def check_tp_sl(self, prices: Dict[str, float]) -> Dict[str, Tuple[Position, float]]:
        """No TP/SL automation for Alpaca live in this stub."""
        return {}


__all__ = ["AlpacaBroker"]
