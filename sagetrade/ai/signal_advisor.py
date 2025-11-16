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
        risk_state = context.get("risk_state") if context else None
        social = signal.social
        lang = getattr(getattr(self._settings, "ai", None), "language", "mix")

        social_part = "no social data"
        if social is not None:
            social_part = (
                f"sentiment={social.sentiment:.3f}, buzz={social.buzz_score:.3f}, "
                f"volume_score={social.volume_score:.3f}"
            )

        nlp_part = (
            f"sentiment={signal.nlp.sentiment:.3f}, impact={signal.nlp.impact_score:.3f}, "
            f"events={signal.nlp.event_flags}"
        )

        risk_equity = getattr(risk_state, "equity", None)
        risk_equity_start = getattr(risk_state, "equity_start", None)
        daily_pnl = getattr(risk_state, "daily_pnl", None)
        open_trades = getattr(risk_state, "open_trades", None)
        total_open_notional = getattr(risk_state, "total_open_notional", None)

        arabic_hint = ""
        if lang == "ar":
            arabic_hint = "\nإذا كانت اللغة عربية، قدّم جملة ملخّص قصيرة بالعربية في النهاية."
        elif lang == "mix":
            arabic_hint = "\nAdd one short Arabic sentence at the end summarizing the decision."

        return (
            'You are "SAGE-RISK-AI", an experienced trading risk advisor.\n'
            "Style:\n"
            "- Conservative and risk-aware.\n"
            "- Clear, concise, non-hype.\n"
            "- Never encourage over-leverage or revenge trading.\n\n"
            "TRADE CONTEXT:\n"
            f"- Symbol: {signal.symbol}\n"
            f"- Strategy: {strat}\n\n"
            "QUANT SIGNALS:\n"
            f"- SMA: {signal.quant.sma:.4f}\n"
            f"- EMA: {signal.quant.ema:.4f}\n"
            f"- RSI: {signal.quant.rsi:.2f}\n"
            f"- ATR: {signal.quant.atr:.4f}\n"
            f"- Volatility: {signal.quant.volatility:.4f}\n"
            f"- Regime: {signal.quant.regime}\n\n"
            "NEWS / NLP:\n"
            f"{nlp_part}\n\n"
            "SOCIAL:\n"
            f"{social_part}\n\n"
            "COMPOSITE SIGNAL:\n"
            f"- Direction: {signal.direction}\n"
            f"- Score: {signal.score:.4f} (approx -1.0 to +1.0)\n"
            f"- Confidence: {signal.confidence:.3f} (0=low, 1=high)\n\n"
            "RISK STATE:\n"
            f"- Current equity: {risk_equity:.2f if risk_equity is not None else 'n/a'}\n"
            f"- Start equity: {risk_equity_start:.2f if risk_equity_start is not None else 'n/a'}\n"
            f"- Daily PnL: {daily_pnl:.2f if daily_pnl is not None else 'n/a'}\n"
            f"- Open trades: {open_trades if open_trades is not None else 'n/a'}\n"
            f"- Total open notional: {total_open_notional:.2f if total_open_notional is not None else 'n/a'}\n\n"
            "TASK:\n"
            "1. Decide if entering NOW is reasonable.\n"
            '2. Choose decision: "approve", "caution", or "reject".\n'
            "3. Optionally suggest better direction (long/short/flat) and confidence (0..1).\n"
            "4. Explain reasoning in 2–3 short sentences.\n"
            "Focus on risk: if daily PnL is negative or exposure high, lean to caution/reject.\n\n"
            "RESPONSE FORMAT (plain text, no JSON, no backticks):\n"
            "decision: <approve|caution|reject>\n"
            "suggested_direction: <long|short|flat|none>\n"
            "suggested_confidence: <0.0-1.0 or 'none'>\n"
            "reason: <2-3 sentences explanation>"
            f"{arabic_hint}\n"
        )


__all__ = ["AISignalAdvice", "AISignalAdvisor"]
