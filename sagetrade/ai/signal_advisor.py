from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sagetrade.signals.aggregator import CompositeSignal


@dataclass
class AISignalAdvice:
    """Lightweight container for AI-generated trade advice."""

    direction: Optional[str] = None
    confidence: float = 0.0
    tp_multiple: float = 0.0
    sl_multiple: float = 0.0
    notes: str = ""


class AISignalAdvisor:
    """Placeholder AI advisor.

    Future versions can call external LLMs to refine direction, confidence,
    and TP/SL suggestions based on CompositeSignal and context.
    """

    def advise(self, signal: CompositeSignal, context: Optional[Dict[str, Any]] = None) -> AISignalAdvice:
        # For now we simply echo the composite signal in a structured form.
        return AISignalAdvice(
            direction=signal.direction,
            confidence=float(signal.confidence),
            notes="AISignalAdvisor is a stub; no external AI calls are made yet.",
        )


__all__ = ["AISignalAdvice", "AISignalAdvisor"]

