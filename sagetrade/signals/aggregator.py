from dataclasses import dataclass
from typing import Dict

from sagetrade.signals.quant import QuantSignals
from sagetrade.signals.nlp import NLPSignals


@dataclass
class CompositeSignal:
    symbol: str
    quant: QuantSignals
    nlp: NLPSignals
    score: float
    direction: str
    confidence: float

    def as_dict(self) -> Dict[str, object]:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "direction": self.direction,
            "confidence": self.confidence,
            "quant": self.quant.as_dict(),
            "nlp": self.nlp.as_dict(),
        }


def aggregate(symbol: str, quant: QuantSignals, nlp: NLPSignals, w_quant: float = 0.6, w_nlp: float = 0.4) -> CompositeSignal:
    """Combine quant + NLP into a single scalar score and direction."""
    # Quant directional component: price vs SMA
    q_score = 0.0
    if quant.sma == quant.sma and quant.sma != 0:  # not NaN
        # hypothetic last close vs SMA proxy via ema
        q_score = (quant.ema - quant.sma) / abs(quant.sma)

    # NLP component: sentiment already in [-1, 1]
    nlp_score = nlp.sentiment
    if nlp.impact_score:
        nlp_score *= 0.5 + 0.5 * nlp.impact_score

    combined = w_quant * q_score + w_nlp * nlp_score

    direction = "flat"
    if combined > 0.01:
        direction = "long"
    elif combined < -0.01:
        direction = "short"

    confidence = min(1.0, abs(combined) * 10.0)

    return CompositeSignal(
        symbol=symbol,
        quant=quant,
        nlp=nlp,
        score=combined,
        direction=direction,
        confidence=confidence,
    )

