from dataclasses import dataclass
from typing import Dict, Optional

from sagetrade.signals.quant import QuantSignals
from sagetrade.signals.nlp import NLPSignals
from sagetrade.signals.social import SocialSignals
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class CompositeSignal:
    symbol: str
    quant: QuantSignals
    nlp: NLPSignals
    score: float
    direction: str
    confidence: float
    social: Optional[SocialSignals] = None

    def as_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "symbol": self.symbol,
            "score": self.score,
            "direction": self.direction,
            "confidence": self.confidence,
            "quant": self.quant.as_dict(),
            "nlp": self.nlp.as_dict(),
        }
        if self.social is not None:
            payload["social"] = {
                "sentiment": self.social.sentiment,
                "buzz_score": self.social.buzz_score,
                "volume_score": self.social.volume_score,
            }
        return payload


def build_composite_signal(
    symbol: str,
    quant: QuantSignals,
    nlp: NLPSignals,
    social: Optional[SocialSignals] = None,
    *,
    quant_weight: float = 0.5,
    news_weight: float = 0.3,
    social_weight: float = 0.2,
    threshold: float = 0.05,
) -> CompositeSignal:
    """Combine quant + NLP (+ optional social) into a single score.

    The scoring is intentionally simple and bounded to [-1, 1] so it can be
    interpreted as a directional "confidence" that strategies can build on.
    """
    # Quant score: normalize RSI from [0, 100] to [-1, 1].
    q_score = 0.0
    rsi_val = quant.rsi
    if rsi_val == rsi_val:  # not NaN
        q_score = max(-1.0, min(1.0, (rsi_val - 50.0) / 50.0))

    # News/NLP score: sentiment already in [-1, 1], scaled by impact_score.
    nlp_score = 0.0
    if nlp is not None:
        nlp_score = nlp.sentiment * max(0.0, nlp.impact_score)

    # Social score: sentiment times buzz (or a floor) if provided.
    social_score = 0.0
    if social is not None:
        social_score = social.sentiment * max(social.buzz_score, 0.0)

    # Weighted combination.
    combined = (
        quant_weight * q_score
        + news_weight * nlp_score
        + social_weight * social_score
    )
    # Clamp to [-1, 1].
    if combined > 1.0:
        combined = 1.0
    elif combined < -1.0:
        combined = -1.0

    # Direction and confidence.
    direction = "flat"
    if combined > threshold:
        direction = "long"
    elif combined < -threshold:
        direction = "short"

    confidence = abs(combined)

    comp = CompositeSignal(
        symbol=symbol,
        quant=quant,
        nlp=nlp,
        score=combined,
        direction=direction,
        confidence=confidence,
        social=social,
    )

    logger.info(
        "composite_signal event=composite_signal symbol=%s direction=%s score=%.4f "
        "confidence=%.3f regime=%s rsi=%.2f",
        symbol,
        direction,
        combined,
        confidence,
        quant.regime,
        quant.rsi,
    )

    return comp


def aggregate(symbol: str, quant: QuantSignals, nlp: NLPSignals, w_quant: float = 0.6, w_nlp: float = 0.4) -> CompositeSignal:
    """Backward-compatible wrapper for older code paths.

    Uses `build_composite_signal` under the hood and maps legacy weights
    into the new scoring scheme (social_weight=0 for now).
    """
    # Normalize weights to sum to 1 for quant/news; ignore social here.
    total = max(w_quant + w_nlp, 1e-9)
    q_w = w_quant / total
    n_w = w_nlp / total
    return build_composite_signal(
        symbol=symbol,
        quant=quant,
        nlp=nlp,
        social=None,
        quant_weight=q_w,
        news_weight=n_w,
        social_weight=0.0,
    )

