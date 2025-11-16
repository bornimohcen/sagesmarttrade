from __future__ import annotations

from typing import Any, Dict, Optional

from sagetrade.ai.client import build_llm_client
from sagetrade.ai.models import AISignalAdvice
from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


class AISignalAdvisor:
    """AI-driven advisor to review a trade idea before execution.

    Currently supports a mock provider; real LLM calls can be wired via the LLM client.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = build_llm_client()

    def advise(self, signal: CompositeSignal, context: Optional[Dict[str, Any]] = None) -> AISignalAdvice:
        # If AI disabled or using mock, emit a simple echo-style advice.
        ai_cfg = getattr(self._settings, "ai", None)
        if not ai_cfg or not getattr(ai_cfg, "enabled", False) or getattr(ai_cfg, "provider", "mock") == "mock":
            return AISignalAdvice(
                symbol=signal.symbol,
                strategy_name=context.get("strategy_name") if context else "unknown",
                decision="caution",
                reason="AI mock mode: echoing composite signal",
                suggested_direction=signal.direction,
                suggested_confidence=float(signal.confidence),
            )

        # Real integration point: send prompt to LLM client.
        prompt = self._build_prompt(signal, context)
        try:
            text = self._client.complete(
                prompt,
                max_tokens=getattr(ai_cfg, "max_output_tokens", 400),
                temperature=0.3,
            )
            # Minimal parser: treat any non-empty as approve.
            decision = "approve"
            return AISignalAdvice(
                symbol=signal.symbol,
                strategy_name=context.get("strategy_name") if context else "unknown",
                decision=decision,  # type: ignore[arg-type]
                reason=text.strip()[:400],
                suggested_direction=signal.direction,
                suggested_confidence=float(signal.confidence),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("ai_signal_advisor_failed event=ai_signal_advisor_failed err=%s", exc)
            return AISignalAdvice(
                symbol=signal.symbol,
                strategy_name=context.get("strategy_name") if context else "unknown",
                decision="caution",
                reason=f"AI unavailable: {exc}",
                suggested_direction=signal.direction,
                suggested_confidence=float(signal.confidence),
            )

    def _build_prompt(self, signal: CompositeSignal, context: Optional[Dict[str, Any]]) -> str:
        strat = context.get("strategy_name") if context else "unknown"
        return (
            "You are an AI trading assistant. Review the trade idea.\n"
            f"Symbol: {signal.symbol}\n"
            f"Strategy: {strat}\n"
            f"Composite direction: {signal.direction}\n"
            f"Composite score: {signal.score:.4f}\n"
            f"Composite confidence: {signal.confidence:.3f}\n"
            f"Quant regime: {signal.quant.regime}, RSI: {signal.quant.rsi:.2f}, "
            f"SMA: {signal.quant.sma:.4f}, EMA: {signal.quant.ema:.4f}\n"
            f"NLP sentiment: {signal.nlp.sentiment:.3f}, impact: {signal.nlp.impact_score:.3f}, "
            f"events: {signal.nlp.event_flags}\n"
            "Provide a brief approval/caution with reasoning and suggested direction/confidence."
        )


__all__ = ["AISignalAdvice", "AISignalAdvisor"]

