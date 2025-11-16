from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class StrategyParamConfig:
    strategy_name: str
    params: Dict[str, Any]


@dataclass
class BacktestExperimentConfig:
    id: str
    symbols: List[str]
    start: Optional[date] = None
    end: Optional[date] = None
    initial_equity: float = 10_000.0
    strategy_params: List[StrategyParamConfig] = None  # type: ignore[assignment]


__all__ = ["StrategyParamConfig", "BacktestExperimentConfig"]

