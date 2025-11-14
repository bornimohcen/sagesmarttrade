from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from sagetrade.execution.models import AccountState, Order, Position, create_market_order
from sagetrade.storage.trade_log import append_trade
from sagetrade.strategy.base import Decision


@dataclass
class PaperBrokerConfig:
    commission_pct: float = 0.0005  # 5 bps per notional
    slippage_pct: float = 0.0005  # 5 bps worst-case slippage


class PaperBroker:
    """Very simple in-memory broker for paper trading.

    - Assumes immediate fills at current price +/- slippage.
    - Tracks account balance and open positions.
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        cfg: PaperBrokerConfig | None = None,
        account_id: str = "paper-default",
    ) -> None:
        self.cfg = cfg or PaperBrokerConfig()
        self.account = AccountState(balance=initial_balance, equity=initial_balance)
        self.orders: Dict[str, Order] = {}
        self.account_id = account_id
        # Map position_id -> originating Decision for richer trade logs.
        self._decision_meta: Dict[str, Decision] = {}

    def _apply_commission(self, notional: float) -> float:
        return notional * self.cfg.commission_pct

    def execute_decision(self, decision: Decision, price: float) -> Tuple[Order, Position]:
        """Translate a Decision into a market order + position, filled immediately."""
        # Notional based on current equity.
        notional = self.account.equity * decision.size_pct
        if notional <= 0:
            raise ValueError("Decision size_pct must be positive.")

        qty = notional / max(price, 1e-8)
        side = decision.side
        order = create_market_order(decision.symbol, side, qty)

        # Slippage: move price slightly against us.
        slip = self.cfg.slippage_pct
        if side == "buy":
            fill_price = price * (1 + slip)
            pos_side = "long"
        else:
            fill_price = price * (1 - slip)
            pos_side = "short"

        order.status = "filled"
        order.filled_qty = qty
        order.avg_fill_price = fill_price
        order.updated_at = time.time()
        self.orders[order.id] = order

        # Commission and account update (balance reduced by commissions only; PnL realized on close).
        commission = self._apply_commission(notional)
        self.account.balance -= commission
        self.account.realized_pnl -= commission
        self.account.equity = self.account.balance

        # Create position with TP/SL levels.
        if decision.take_profit_pct != 0:
            if pos_side == "long":
                tp = fill_price * (1 + decision.take_profit_pct)
            else:
                tp = fill_price * (1 - decision.take_profit_pct)
        else:
            tp = None

        if decision.stop_loss_pct != 0:
            if pos_side == "long":
                sl = fill_price * (1 - decision.stop_loss_pct)
            else:
                sl = fill_price * (1 + decision.stop_loss_pct)
        else:
            sl = None

        position = Position(
            id=order.id.replace("ord", "pos"),
            symbol=decision.symbol,
            side=pos_side,
            qty=qty,
            entry_price=fill_price,
            take_profit=tp,
            stop_loss=sl,
            opened_at=order.created_at,
        )
        self.account.positions[position.id] = position

        # Remember decision metadata so we can log a richer trade on close.
        self._decision_meta[position.id] = decision

        return order, position

    def close_position(self, position_id: str, price: float) -> Tuple[Position, float]:
        """Close a position at the given price and update account.

        Returns the closed Position (with realized_pnl set) and the notional used for risk tracking.
        """
        if position_id not in self.account.positions:
            raise KeyError(f"Unknown position id: {position_id}")

        pos = self.account.positions.pop(position_id)
        notional = pos.entry_price * pos.qty

        if pos.side == "long":
            gross_pnl = (price - pos.entry_price) * pos.qty
        else:
            gross_pnl = (pos.entry_price - price) * pos.qty

        commission = self._apply_commission(notional)
        pnl = gross_pnl - commission

        self.account.balance += pnl
        self.account.realized_pnl += pnl
        self.account.equity = self.account.balance

        closed_ts = time.time()
        pos.closed_at = closed_ts
        pos.realized_pnl = pnl

        # Persist trade history for this (paper) account.
        meta = self._decision_meta.pop(position_id, None)
        duration_sec = int(max(0.0, closed_ts - pos.opened_at))
        size_pct = meta.size_pct if meta is not None else None
        strategy = meta.strategy_name if meta is not None else None
        reason = meta.reason if meta is not None else None
        pnl_pct = (pnl / notional * 100.0) if notional > 0 else 0.0

        trade_record = {
            "trade_id": position_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(closed_ts)),
            "account_id": self.account_id,
            "environment": "paper",
            "symbol": pos.symbol,
            "side": pos.side,
            "qty": pos.qty,
            "size_pct": size_pct,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "duration_seconds": duration_sec,
            "strategy": strategy,
            "reason": reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        }
        append_trade(self.account_id, trade_record)

        return pos, notional

    def check_tp_sl(self, prices: Dict[str, float]) -> Dict[str, Tuple[Position, float]]:
        """Evaluate TP/SL for all positions and close those that hit.

        Returns a dict mapping position_id -> (closed_position, notional).
        """
        to_close: list[Tuple[str, float]] = []
        for pos_id, pos in self.account.positions.items():
            price = prices.get(pos.symbol)
            if price is None:
                continue

            hit_tp = False
            hit_sl = False

            if pos.take_profit is not None:
                if pos.side == "long" and price >= pos.take_profit:
                    hit_tp = True
                elif pos.side == "short" and price <= pos.take_profit:
                    hit_tp = True

            if not hit_tp and pos.stop_loss is not None:
                if pos.side == "long" and price <= pos.stop_loss:
                    hit_sl = True
                elif pos.side == "short" and price >= pos.stop_loss:
                    hit_sl = True

            if hit_tp or hit_sl:
                to_close.append((pos_id, price))

        result: Dict[str, Tuple[Position, float]] = {}
        for pos_id, exit_price in to_close:
            closed, notional = self.close_position(pos_id, exit_price)
            result[pos_id] = (closed, notional)
        return result

    def summary(self) -> dict:
        open_notional = 0.0
        for pos in self.account.positions.values():
            open_notional += pos.qty * pos.entry_price
        return {
            "balance": self.account.balance,
            "equity": self.account.equity,
            "realized_pnl": self.account.realized_pnl,
            "open_positions": len(self.account.positions),
            "open_notional": open_notional,
        }
