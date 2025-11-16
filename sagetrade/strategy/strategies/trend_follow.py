from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Decision, Strategy
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class TrendFollowConfig:
    min_confidence: float = 0.2
    size_pct: float = 0.001  # 0.1% of equity
    take_profit_pct: float = 0.004  # 0.4%
    stop_loss_pct: float = 0.006  # 0.6%
    target_duration_sec: int = 900  # 15 minutes
    max_rsi_for_long: float = 70.0
    min_rsi_for_long: float = 50.0
    min_rsi_for_short: float = 30.0
    max_rsi_for_short: float = 50.0


class TrendFollow(Strategy):
    """Simple trend-following strategy based on EMA vs SMA and RSI."""

    name = "trend_follow"

    def __init__(self) -> None:
        self.cfg = TrendFollowConfig()
        self._logger = get_logger(__name__)

    def initialize(self, config: Dict[str, Any]) -> None:
        for field in self.cfg.__dataclass_fields__.keys():
            if field in config:
                setattr(self.cfg, field, config[field])

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        q = signal.quant

        if signal.confidence < self.cfg.min_confidence:
            return None

        side: Optional[str] = None

        # Trending up: EMA above SMA and RSI in mid-upper range.
        if q.ema > q.sma and self.cfg.min_rsi_for_long < q.rsi < self.cfg.max_rsi_for_long:
            side = "buy"

        # Trending down: EMA below SMA and RSI in mid-lower range.
        elif q.ema < q.sma and self.cfg.min_rsi_for_short < q.rsi < self.cfg.max_rsi_for_short:
            side = "sell"

        if side is None:
            return None

        decision = Decision(
            symbol=signal.symbol,
            strategy_name=self.name,
            side=side,
            size_pct=self.cfg.size_pct,
            order_type="market",
            limit_price=None,
            take_profit_pct=self.cfg.take_profit_pct,
            stop_loss_pct=self.cfg.stop_loss_pct,
            target_duration_sec=self.cfg.target_duration_sec,
            reason=(
                f"TrendFollow: ema={q.ema:.4f}, sma={q.sma:.4f}, rsi={q.rsi:.2f}, "
                f"direction={signal.direction}, confidence={signal.confidence:.2f}"
            ),
        )

        self._logger.info(
            "strategy_decision event=strategy_decision strategy=%s symbol=%s side=%s "
            "ema=%.4f sma=%.4f rsi=%.2f score=%.4f confidence=%.3f",
            self.name,
            signal.symbol,
            side,
            q.ema,
            q.sma,
            q.rsi,
            signal.score,
            signal.confidence,
        )

        return decision

    def on_tick(self, market_state: Dict[str, Any]) -> list[Decision]:
        # No separate tick-based logic yet.
        return []


