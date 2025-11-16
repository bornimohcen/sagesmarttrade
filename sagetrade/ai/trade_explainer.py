from __future__ import annotations

from typing import Any, Dict, Optional

from sagetrade.ai.client import build_llm_client
from sagetrade.ai.models import AITradeExplanation
from sagetrade.signals.aggregator import CompositeSignal
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


def explain_before_trade(
    symbol: str,
    signal: CompositeSignal,
    strategy_name: str = "unknown",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Human-readable pre-trade explanation (compatible with existing callers)."""
    return (
        f"Pre-trade: symbol={symbol}, strategy={strategy_name}, "
        f"direction={signal.direction}, score={signal.score:.4f}, confidence={signal.confidence:.2f}."
    )


def explain_after_trade(symbol: str, trade_summary: Dict[str, Any]) -> str:
    """Human-readable post-trade explanation (compatible with existing callers)."""
    pnl = trade_summary.get("pnl")
    pnl_str = f"{pnl:.2f}" if isinstance(pnl, (int, float)) else str(pnl)
    return f"Post-trade summary for {symbol}: PnL={pnl_str}. Detailed AI review not implemented yet."


def explain_open_trade_ai(
    symbol: str,
    signal: CompositeSignal,
    strategy_name: str,
    risk_state: Any,
) -> AITradeExplanation:
    """Return AITradeExplanation (stub/LLM) for an open trade."""
    settings = get_settings()
    ai_cfg = getattr(settings, "ai", None)
    client = build_llm_client()

    if not ai_cfg or not getattr(ai_cfg, "enabled", False) or getattr(ai_cfg, "provider", "mock") == "mock":
        return AITradeExplanation(
            symbol=symbol,
            strategy_name=strategy_name,
            title="AI mock explanation",
            summary=(
                f"Signal suggests {signal.direction} with score={signal.score:.3f} "
                f"and confidence={signal.confidence:.2f}. (AI mock mode)"
            ),
            risks=[
                f"Regime: {signal.quant.regime}",
                f"RSI: {signal.quant.rsi:.2f}",
            ],
            notes=["Enable AI provider to get richer explanations."],
        )

    prompt = _build_explain_open_prompt(symbol, signal, strategy_name, risk_state, ai_cfg.language)
    try:
        text = client.complete(prompt, max_tokens=getattr(ai_cfg, "max_output_tokens", 400), temperature=0.4)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("ai_trade_explainer_failed event=ai_trade_explainer_failed err=%s", exc)
        text = f"AI unavailable: {exc}"

    return AITradeExplanation(
        symbol=symbol,
        strategy_name=strategy_name,
        title=f"Trade idea for {symbol}",
        summary=text[:400],
        risks=[f"Regime={signal.quant.regime}", f"RSI={signal.quant.rsi:.2f}"],
        notes=["AI explanation generated."],
    )


def explain_closed_trade_ai(
    symbol: str,
    pnl: float,
    holding_seconds: float,
    strategy_name: str,
    signal_at_entry: CompositeSignal,
) -> AITradeExplanation:
    """Return AITradeExplanation for a closed trade."""
    settings = get_settings()
    ai_cfg = getattr(settings, "ai", None)
    client = build_llm_client()

    if not ai_cfg or not getattr(ai_cfg, "enabled", False) or getattr(ai_cfg, "provider", "mock") == "mock":
        return AITradeExplanation(
            symbol=symbol,
            strategy_name=strategy_name,
            title="AI mock post-trade",
            summary=f"Trade closed with PnL={pnl:.2f} after {holding_seconds:.0f}s. (AI mock mode)",
            risks=[],
            notes=["Enable AI provider to get richer post-trade analysis."],
        )

    prompt = _build_explain_closed_prompt(
        symbol, pnl, holding_seconds, strategy_name, signal_at_entry, ai_cfg.language
    )
    try:
        text = client.complete(prompt, max_tokens=getattr(ai_cfg, "max_output_tokens", 400), temperature=0.4)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("ai_trade_explainer_failed event=ai_trade_explainer_failed err=%s", exc)
        text = f"AI unavailable: {exc}"

    return AITradeExplanation(
        symbol=symbol,
        strategy_name=strategy_name,
        title=f"Trade review for {symbol}",
        summary=text[:400],
        risks=[],
        notes=["AI post-trade review generated."],
    )


def _build_explain_open_prompt(
    symbol: str,
    signal: CompositeSignal,
    strategy_name: str,
    risk_state: Any,
    language: str = "mix",
) -> str:
    nlp_text = (
        f"sentiment={signal.nlp.sentiment:.3f}, impact={signal.nlp.impact_score:.3f}, "
        f"events={signal.nlp.event_flags}"
    )
    social_text = "no social data"
    if signal.social is not None:
        s = signal.social
        social_text = f"sentiment={s.sentiment:.3f}, buzz={s.buzz_score:.3f}, volume_score={s.volume_score:.3f}"

    lang_hint = ""
    if language == "ar":
        lang_hint = "\nWrite the entire response in Arabic (you may keep key financial terms in English)."
    elif language == "mix":
        lang_hint = "\nLanguage: English, but add ONE short Arabic sentence at the end of SUMMARY."

    return (
        'You are "SAGE-EXPLAIN-AI", an AI trading assistant.\n'
        "Explain the newly opened trade to a trader (non-quant expert).\n\n"
        f"TRADE:\n- Symbol: {symbol}\n- Strategy: {strategy_name}\n- Side: {signal.direction}\n"
        f"- Quantity: n/a\n- Entry price: n/a\n\n"
        "QUANT SIGNALS (last window):\n"
        f"- SMA: {signal.quant.sma:.4f}\n"
        f"- EMA: {signal.quant.ema:.4f}\n"
        f"- RSI: {signal.quant.rsi:.2f}\n"
        f"- ATR: {signal.quant.atr:.4f}\n"
        f"- Volatility: {signal.quant.volatility:.4f}\n"
        f"- Regime: {signal.quant.regime}\n\n"
        "COMPOSITE SIGNAL:\n"
        f"- Direction: {signal.direction}\n"
        f"- Score: {signal.score:.4f}\n"
        f"- Confidence: {signal.confidence:.3f}\n\n"
        f"NEWS / NLP:\n{nlp_text}\n\n"
        f"SOCIAL:\n{social_text}\n\n"
        "RISK CONTEXT:\n"
        f"- Current equity: {getattr(risk_state, 'equity', 'n/a')}\n"
        f"- Start equity: {getattr(risk_state, 'equity_start', 'n/a')}\n"
        f"- Open trades: {getattr(risk_state, 'open_trades', 'n/a')}\n"
        f"- Total open notional: {getattr(risk_state, 'total_open_notional', 'n/a')}\n\n"
        "TASK:\n"
        "1) Give a short TITLE summarizing the idea in ONE line.\n"
        "2) Give a SUMMARY (3–5 sentences): why enter now, how signals support, how aggressive/conservative. "
        "End SUMMARY with one short Arabic sentence.\n"
        "3) Provide 2–4 RISKS (bullet style).\n"
        "4) Provide 1–3 NOTES (bullet style) on managing the trade.\n\n"
        "RESPONSE FORMAT (plain text, no JSON, no markdown):\n"
        "TITLE: <short title>\n"
        "SUMMARY: <paragraph including the Arabic sentence at the end>\n"
        "RISKS:\n- <risk 1>\n- <risk 2>\n- <risk 3>\n"
        "NOTES:\n- <note 1>\n- <note 2>\n- <note 3>\n"
        f"{lang_hint}\n"
    )


def _build_explain_closed_prompt(
    symbol: str,
    pnl: float,
    holding_seconds: float,
    strategy_name: str,
    signal: CompositeSignal,
    language: str = "mix",
) -> str:
    lang_hint = ""
    if language == "ar":
        lang_hint = "\nاكتب المراجعة بالعربية مع الإبقاء على المصطلحات المالية الأساسية بالإنجليزية عند الحاجة."
    elif language == "mix":
        lang_hint = "\nLanguage: English, add one short Arabic sentence at the end of LESSON."

    return (
        'You are "SAGE-REVIEW-AI", an AI trading mentor.\n'
        "Review the completed trade and extract lessons.\n\n"
        "TRADE SUMMARY:\n"
        f"- Symbol: {symbol}\n"
        f"- Strategy: {strategy_name}\n"
        f"- PnL: {pnl:.2f}\n"
        f"- Holding seconds: {holding_seconds:.0f}\n\n"
        "ENTRY SIGNAL SNAPSHOT:\n"
        f"- Direction: {signal.direction}\n"
        f"- Score: {signal.score:.4f}\n"
        f"- Confidence: {signal.confidence:.3f}\n"
        f"- Regime: {signal.quant.regime}\n"
        f"- RSI: {signal.quant.rsi:.2f}\n\n"
        "TASK:\n"
        "1) Classify OUTCOME as win, loss, or breakeven.\n"
        "2) Give a 2–4 sentence LESSON explaining what went right/wrong.\n"
        "3) Provide 2–4 IMPROVEMENTS (bullet points) for future trades.\n\n"
        "RESPONSE FORMAT:\n"
        "OUTCOME: <win|loss|breakeven>\n"
        "LESSON: <one paragraph>\n"
        "IMPROVEMENTS:\n- <improvement 1>\n- <improvement 2>\n- <improvement 3>\n"
        f"{lang_hint}\n"
    )


__all__ = [
    "explain_before_trade",
    "explain_after_trade",
    "explain_open_trade_ai",
    "explain_closed_trade_ai",
]
