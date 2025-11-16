from __future__ import annotations

"""Compatibility wrapper for news/NLP signals.

This module re-exports the existing NLPSignals dataclass from `nlp` and
provides a neutral placeholder `compute_nlp_news_signals` helper so that
documentation and code can converge on a single interface.
"""

from sagetrade.signals.nlp import NLPSignals
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


def compute_nlp_news_signals(entity: str) -> NLPSignals:
    """Return neutral NLP/news signals for the given entity.

    Real implementations can later call into `sagetrade.signals.nlp.get_signals`
    with actual text items from ingestion. For now we keep the shape stable
    and log debug information for observability.
    """
    sentiment = 0.0
    impact_score = 0.0
    event_flags = {"earnings": False, "ma": False, "guidance": False}

    logger.debug(
        "nlp_news_signals_placeholder event=nlp_news_signals entity=%s sentiment=%.3f impact=%.3f",
        entity,
        sentiment,
        impact_score,
    )

    return NLPSignals(
        entity=entity,
        sentiment=sentiment,
        event_flags=event_flags,
        impact_score=impact_score,
        language=None,
    )


__all__ = ["NLPSignals", "compute_nlp_news_signals"]

