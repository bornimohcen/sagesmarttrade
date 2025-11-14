from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Decision, Strategy


@dataclass
class NewsQuickTradeConfig:
    min_impact: float = 0.1
    min_sentiment_abs: float = 0.003
    size_pct: float = 0.005  # 0.5% of equity per trade
    take_profit_pct: float = 0.0025
    stop_loss_pct: float = 0.004
    target_duration_sec: int = 300  # 5 minutes


class NewsQuickTrade(Strategy):
    name = "news_quick_trade"

    def __init__(self) -> None:
        self.cfg = NewsQuickTradeConfig()

    def initialize(self, config: Dict[str, Any]) -> None:
        for field in self.cfg.__dataclass_fields__.keys():
            if field in config:
                setattr(self.cfg, field, config[field])

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        nlp = signal.nlp

        # Skip trades when composite direction is flat; avoid trading on noisy signals.
        if signal.direction == "flat":
            return None

        if nlp.impact_score < self.cfg.min_impact:
            return None

        if abs(nlp.sentiment) < self.cfg.min_sentiment_abs:
            return None

        side = "buy" if nlp.sentiment > 0 else "sell"

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
                f"NewsQuickTrade: sentiment={nlp.sentiment:.2f}, impact={nlp.impact_score:.2f}, "
                f"events={nlp.event_flags}"
            ),
        )
