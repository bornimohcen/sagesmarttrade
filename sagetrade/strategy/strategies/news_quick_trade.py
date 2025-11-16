from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Decision, Strategy
from sagetrade.strategy.params import NewsQuickTradeParams
from sagetrade.utils.logging import get_logger


@dataclass
class NewsQuickTradeConfig:
    size_pct: float = 0.005  # fallback if params.risk_factor not used
    take_profit_pct: float = 0.0025
    stop_loss_pct: float = 0.004
    target_duration_sec: int = 300  # 5 minutes


class NewsQuickTrade(Strategy):
    name = "news_quick_trade"

    def __init__(self, params: Optional[NewsQuickTradeParams] = None) -> None:
        self.cfg = NewsQuickTradeConfig()
        self.params = params or NewsQuickTradeParams()
        self._logger = get_logger(__name__)

    def initialize(self, config: Dict[str, Any]) -> None:
        for field in self.cfg.__dataclass_fields__.keys():
            if field in config:
                setattr(self.cfg, field, config[field])

    def on_new_signal(self, signal: CompositeSignal) -> Optional[Decision]:
        nlp = signal.nlp
        p = self.params

        # Skip trades when composite direction is flat; avoid trading on noisy signals.
        if signal.direction == "flat":
            return None

        if nlp.impact_score < p.min_impact_score:
            return None

        if abs(nlp.sentiment) < p.min_abs_sentiment:
            return None

        if signal.confidence < p.min_confidence:
            return None

        if p.require_high_vol_regime and signal.quant.regime != "high_vol":
            return None

        side = "buy" if nlp.sentiment > 0 else "sell"

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
                f"NewsQuickTrade: sentiment={nlp.sentiment:.2f}, impact={nlp.impact_score:.2f}, "
                f"events={nlp.event_flags}"
            ),
        )

        self._logger.info(
            "strategy_decision event=strategy_decision strategy=%s symbol=%s side=%s "
            "score=%.4f confidence=%.3f sentiment=%.4f impact=%.4f",
            self.name,
            signal.symbol,
            side,
            signal.score,
            signal.confidence,
            nlp.sentiment,
            nlp.impact_score,
        )

        return decision
