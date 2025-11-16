from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SymbolAllocation:
    target_weight: float
    max_weight: float = 0.3
    max_concurrent_trades: int = 3


@dataclass
class StrategyAllocation:
    target_weight: float
    max_weight: float


@dataclass
class AssetClassAllocation:
    target_weight: float
    max_weight: float


@dataclass
class PortfolioConfig:
    symbols: Dict[str, SymbolAllocation] = field(default_factory=dict)
    strategies: Dict[str, StrategyAllocation] = field(default_factory=dict)
    asset_classes: Dict[str, AssetClassAllocation] = field(default_factory=dict)
    max_total_leverage: float = 1.0
    max_positions: int = 50


__all__ = ["SymbolAllocation", "StrategyAllocation", "AssetClassAllocation", "PortfolioConfig"]

