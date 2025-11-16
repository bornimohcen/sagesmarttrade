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

    prompt = _build_explain_open_prompt(symbol, signal, strategy_name, risk_state)
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

    prompt = _build_explain_closed_prompt(symbol, pnl, holding_seconds, strategy_name, signal_at_entry)
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


def _build_explain_open_prompt(symbol: str, signal: CompositeSignal, strategy_name: str, risk_state: Any) -> str:
    return (
        "Explain briefly the trade idea for Telegram:\n"
        f"Symbol: {symbol}\n"
        f"Strategy: {strategy_name}\n"
        f"Direction: {signal.direction}\n"
        f"Score: {signal.score:.4f}\n"
        f"Confidence: {signal.confidence:.3f}\n"
        f"Quant: regime={signal.quant.regime}, rsi={signal.quant.rsi:.2f}, sma={signal.quant.sma:.4f}, ema={signal.quant.ema:.4f}\n"
        f"NLP: sentiment={signal.nlp.sentiment:.3f}, impact={signal.nlp.impact_score:.3f}, events={signal.nlp.event_flags}\n"
        f"Risk: equity={getattr(risk_state, 'equity', 'n/a')}, open_trades={getattr(risk_state, 'open_trades', 'n/a')}\n"
        "Return a short summary and bullet risks."
    )


def _build_explain_closed_prompt(symbol: str, pnl: float, holding_seconds: float, strategy_name: str, signal: CompositeSignal) -> str:
    return (
        "Summarize the closed trade:\n"
        f"Symbol: {symbol}\n"
        f"Strategy: {strategy_name}\n"
        f"PnL: {pnl:.2f}\n"
        f"Holding seconds: {holding_seconds:.0f}\n"
        f"Entry signal: direction={signal.direction}, score={signal.score:.4f}, confidence={signal.confidence:.3f}, regime={signal.quant.regime}\n"
        "Provide 2-3 bullet risks/lessons."
    )


__all__ = [
    "explain_before_trade",
    "explain_after_trade",
    "explain_open_trade_ai",
    "explain_closed_trade_ai",
]

