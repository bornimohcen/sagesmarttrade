from __future__ import annotations

from dataclasses import dataclass

from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class SocialSignals:
    """Lightweight social-sentiment snapshot for a symbol."""

    symbol: str
    sentiment: float  # -1 .. 1
    buzz_score: float  # 0 .. 1 (engagement / hype)
    volume_score: float  # 0 .. 1 (activity vs history)


def compute_social_signals(symbol: str) -> SocialSignals:
    """Placeholder social signals until real ingestion is wired.

    Returns neutral signals (no strong social push). This shape is stable so
    it can later be backed by real social data without changing call sites.
    """
    sentiment = 0.0
    buzz = 0.0
    volume = 0.0

    logger.debug(
        "social_signals_placeholder event=social_signals symbol=%s sentiment=%.3f buzz=%.3f volume=%.3f",
        symbol,
        sentiment,
        buzz,
        volume,
    )

    return SocialSignals(symbol=symbol, sentiment=sentiment, buzz_score=buzz, volume_score=volume)


__all__ = ["SocialSignals", "compute_social_signals"]

