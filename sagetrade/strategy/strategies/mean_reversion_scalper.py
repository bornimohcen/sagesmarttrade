from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Decision, Strategy


@dataclass
class MeanReversionScalperConfig:
    min_confidence: float = 0.15
    overbought_rsi: float = 70.0
    oversold_rsi: float = 30.0
    size_pct: float = 0.001
    take_profit_pct: float = 0.002
    stop_loss_pct: float = 0.004
    target_duration_sec: int = 600  # 10 minutes


class MeanReversionScalper(Strategy):
    name = "mean_reversion_scalper"

    def __init__(self) -> None:
        self.cfg = MeanReversionScalperConfig()

    def initialize(self, config: Dict[str, Any]) -> None:
        for field in self.cfg.__dataclass_fields__.keys():
            if field in config:
                setattr(self.cfg, field, config[field])

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        q = signal.quant

        if signal.confidence < self.cfg.min_confidence:
            return None

        # Prefer high volatility regimes for mean reversion scalps.
        if q.regime not in {"normal", "high_vol"}:
            return None

        side: Optional[str] = None
        # Overbought: short for mean reversion.
        if q.rsi >= self.cfg.overbought_rsi:
            side = "sell"
        # Oversold: buy for rebound.
        elif q.rsi <= self.cfg.oversold_rsi:
            side = "buy"

        if side is None:
            return None

        return Decision(
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
                f"MeanReversionScalper: rsi={q.rsi:.1f}, regime={q.regime}, "
                f"confidence={signal.confidence:.2f}"
            ),
        )


