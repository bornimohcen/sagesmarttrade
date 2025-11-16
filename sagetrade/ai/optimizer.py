from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class OptimizationRequest:
    strategy_name: str
    params: Dict[str, Any]


@dataclass
class OptimizationResult:
    strategy_name: str
    suggested_params: Dict[str, Any]
    notes: str = ""


class AIOptimizer:
    """Placeholder for AI-assisted hyperparameter optimization."""

    def propose(self, request: OptimizationRequest) -> OptimizationResult:
        # Stub: in the future, this can call an AI service and/or run backtests.
        return OptimizationResult(
            strategy_name=request.strategy_name,
            suggested_params=request.params,
            notes="AIOptimizer is a stub; parameters are echoed unchanged.",
        )


__all__ = ["OptimizationRequest", "OptimizationResult", "AIOptimizer"]

