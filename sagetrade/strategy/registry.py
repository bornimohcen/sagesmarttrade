from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Type

from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.strategy.base import Strategy
from sagetrade.strategy.strategies.mean_reversion_scalper import MeanReversionScalper
from sagetrade.strategy.strategies.momentum_scalper import MomentumScalper
from sagetrade.strategy.strategies.news_quick_trade import NewsQuickTrade


STRATEGY_CLASSES: Dict[str, Type[Strategy]] = {
    "momentum_scalper": MomentumScalper,
    "mean_reversion_scalper": MeanReversionScalper,
    "news_quick_trade": NewsQuickTrade,
}


@dataclass
class StrategyConfig:
    name: str
    enabled: bool = True
    min_confidence: float = 0.0
    allowed_regimes: List[str] | None = None


class StrategyManager:
    """Registers strategies and decides which ones are active for a given signal."""

    def __init__(self, configs: Dict[str, StrategyConfig] | None = None) -> None:
        if configs is None:
            configs = self._build_default_configs()
        self.configs = configs
        self.strategies: Dict[str, Strategy] = {}
        self._instantiate_strategies()

    def _build_default_configs(self) -> Dict[str, StrategyConfig]:
        return {
            "momentum_scalper": StrategyConfig(
                name="momentum_scalper",
                enabled=True,
                min_confidence=0.2,
                allowed_regimes=["normal", "high_vol"],
            ),
            "mean_reversion_scalper": StrategyConfig(
                name="mean_reversion_scalper",
                enabled=True,
                min_confidence=0.15,
                allowed_regimes=["normal", "high_vol"],
            ),
            "news_quick_trade": StrategyConfig(
                name="news_quick_trade",
                enabled=True,
                min_confidence=0.0,
                allowed_regimes=["low_vol", "normal", "high_vol"],
            ),
        }

    def _instantiate_strategies(self) -> None:
        enabled_override = os.environ.get("STRATEGIES_ENABLED")
        disabled_override = os.environ.get("STRATEGIES_DISABLED")
        enabled_list = None
        disabled_list = None
        if enabled_override:
            enabled_list = {s.strip() for s in enabled_override.split(",") if s.strip()}
        if disabled_override:
            disabled_list = {s.strip() for s in disabled_override.split(",") if s.strip()}

        for name, cfg in self.configs.items():
            if enabled_list is not None:
                cfg.enabled = name in enabled_list
            if disabled_list is not None and name in disabled_list:
                cfg.enabled = False

            if not cfg.enabled:
                continue

            cls = STRATEGY_CLASSES.get(name)
            if not cls:
                continue
            inst = cls()
            # Pass config fields that match underlying strategy config if any.
            inst.initialize(
                {
                    "min_confidence": cfg.min_confidence,
                }
            )
            self.strategies[name] = inst

    def select_for_signal(self, signal: CompositeSignal) -> List[Strategy]:
        """Return strategies that are allowed for this signal (regime + confidence)."""
        out: List[Strategy] = []
        for name, strat in self.strategies.items():
            cfg = self.configs.get(name)
            if not cfg or not cfg.enabled:
                continue
            if signal.confidence < cfg.min_confidence:
                continue
            if cfg.allowed_regimes is not None and signal.quant.regime not in cfg.allowed_regimes:
                continue
            out.append(strat)
        return out


