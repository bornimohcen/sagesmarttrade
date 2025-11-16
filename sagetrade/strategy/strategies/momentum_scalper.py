from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Decision, Strategy
from sagetrade.utils.logging import get_logger


@dataclass
class MomentumScalperConfig:
    min_confidence: float = 0.2
    max_rsi_for_long: float = 70.0
    min_rsi_for_short: float = 30.0
    size_pct: float = 0.001  # 0.1%
    take_profit_pct: float = 0.003  # 0.3%
    stop_loss_pct: float = 0.005  # 0.5%
    target_duration_sec: int = 300  # 5 minutes


class MomentumScalper(Strategy):
    name = "momentum_scalper"

    def __init__(self) -> None:
        self.cfg = MomentumScalperConfig()
        self._logger = get_logger(__name__)

    def initialize(self, config: Dict[str, Any]) -> None:
        for field in self.cfg.__dataclass_fields__.keys():
            if field in config:
                setattr(self.cfg, field, config[field])

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        q = signal.quant

        if signal.confidence < self.cfg.min_confidence:
            return None

        if q.regime == "low_vol":
            return None

        # Simple momentum logic: follow composite direction, gated by RSI.
        side: Optional[str] = None
        if signal.direction == "long" and q.rsi <= self.cfg.max_rsi_for_long:
            side = "buy"
        elif signal.direction == "short" and q.rsi >= self.cfg.min_rsi_for_short:
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
                f"MomentumScalper: direction={signal.direction}, "
                f"confidence={signal.confidence:.2f}, rsi={q.rsi:.1f}, regime={q.regime}"
            ),
        )

        self._logger.info(
            "strategy_decision event=strategy_decision strategy=%s symbol=%s side=%s "
            "score=%.4f confidence=%.3f rsi=%.2f regime=%s",
            self.name,
            signal.symbol,
            side,
            signal.score,
            signal.confidence,
            q.rsi,
            q.regime,
        )

        return decision

