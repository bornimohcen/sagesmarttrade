from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NewsQuickTradeParams:
    min_impact_score: float = 0.3
    min_abs_sentiment: float = 0.2
    min_confidence: float = 0.3
    require_high_vol_regime: bool = True
    risk_factor: float = 2.0  # multiplier on global max_risk_per_trade_pct


@dataclass
class TrendFollowParams:
    rsi_long_min: float = 50.0
    rsi_long_max: float = 70.0
    rsi_short_min: float = 30.0
    rsi_short_max: float = 50.0
    min_confidence: float = 0.2
    risk_factor: float = 3.0


__all__ = ["NewsQuickTradeParams", "TrendFollowParams"]

