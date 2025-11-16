Part 9 = AI Brain حقيقي فوق النظام كامل:
يساعد في تصفية الإشارات، شرح الصفقات، ومراجعة الأداء + يطلع الكلام الحلو على تيليغرام.

رح أعمله لك كالتالي:

الفكرة العامة لطبقة الـ AI في المشروع

تقسيم Part 9 لمهام واضحة

تصميم الـ Data Models (AISignalAdvice, TradeExplanation, TradeReview)

تصميم LLM Client عام (بدون ربط بمزوّد معيّن)

AISignalAdvisor: كيف يتدخل قبل تنفيذ الصفقة

AITradeExplainer: كيف يشرح الصفقة بلغة طبيعية (لتيليغرام واللوج)

دمج AI مع Telegram bot (أوامر مثل /explain_last)

إضافة إعدادات الـ AI في settings.yaml

Prompt جاهز تعطيه لـ AI Agent ينفذ Part 9 على الكود

🧠 1) ما هي طبقة الـ AI اللي نريدها في SAGE SmartTrade؟

نريد ثلاث أدوار رئيسية:

AISignalAdvisor

يأخذ CompositeSignal + RiskState + StrategyProposal

يراجعها (conceptually)

يرجع:

هل يرى أن الصفقة منطقية؟ (approve / caution / reject_suggest_flat)

إن أحببت: تعديل بسيط في direction أو confidence

تعليق قصير “Reasoning” (يُستخدم في اللوج و telegram)

AITradeExplainer

بعد فتح صفقة (أو إغلاقها)، يأخذ:

CompositeSignal

الاستراتيجية

حجم المخاطرة

سبب الدخول/الخروج

يطلع نص واضح (بالعربية/الإنجليزية) يشرح:

لماذا دخلنا؟

ما هي المخاطر؟

كيف نتابع الصفقة؟

Post-Trade Reviewer (اختياري الآن)

بعد إغلاق الصفقة:

يعمل “mini report”: ماذا تعلمنا من الصفقة؟

ممكن نؤجله للمرحلة القادمة، لكن نجهّز له واجهة (Interface).

🧩 2) تقسيم Part 9 إلى مهام
🧱 9.1 — إضافة إعدادات AI في config/settings.yaml

قسم ai::

provider (مثلاً "openai", "local", "mock")

model

max_tokens

language (en/ar)

مفتاح API عبر Env vars

🧱 9.2 — تصميم Data Models لطبقة AI

ملف: sagetrade/ai/models.py

AISignalAdvice

AITradeExplanation

(اختياري) AITradeReview

🧱 9.3 — LLMClient abstraction

ملف: sagetrade/ai/client.py

LLMClientBase (interface)

EnvLLMClient (يقرأ مفتاح من env، يرسل prompt ويرجع نص)

حالياً نخليه “stub” (أنت لاحقاً تربطه بـ OpenAI أو غيره).

🧱 9.4 — AISignalAdvisor

ملف: sagetrade/ai/signal_advisor.py

دالة / كلاس:

AISignalAdvisor.review_trade_candidate(symbol, composite, strategy_name, risk_state) -> AISignalAdvice

يبني prompt نصي من:

الاتجاه، score, confidence

حالة المخاطر

نوع الاستراتيجية

ينادي LLMClient → يرجع advice + reasoning

لو API مش متوفر → fallback (منطق rule-based بسيط)

🧱 9.5 — AITradeExplainer

ملف: sagetrade/ai/trade_explainer.py

دالة:

explain_open_trade(order, position, composite, strategy_name, risk_state) -> AITradeExplanation

explain_closed_trade(position, pnl, holding_period, composite_at_entry, strategy_name) -> AITradeExplanation

تستخدم LLMClient لإنتاج نص explanation جاهز لتيليغرام.

🧱 9.6 — دمج AI مع Trading Loop + Telegram bot

قبل إرسال order:

نستدعي AISignalAdvisor

نقدر:

نطلب منه approval منطقي (مثلاً لو قال reject → ننفذ rule “احترام AI” أو لا)

نسجّل رأيه في اللوج.

بعد تنفيذ order:

نطلب من AITradeExplainer نص explanation

إذا تيليغرام مفعّل:

نرسل النص للمستخدم

Telegram commands:

/explain_last → يجيب آخر صفقة + explanation

/explain_open → يشرح كل الصفقات المفتوحة الحاليّة

/why_blocked → يشرح آخر صفقة تم حظرها من RiskManager

📄 3) Data Models لطبقة AI
ملف: sagetrade/ai/models.py
# FILE: sagetrade/ai/models.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal, List

AISignalDecision = Literal["approve", "caution", "reject"]

@dataclass
class AISignalAdvice:
    symbol: str
    strategy_name: str
    decision: AISignalDecision
    reason: str
    suggested_direction: Optional[str] = None     # "long", "short", "flat"
    suggested_confidence: Optional[float] = None  # 0..1

@dataclass
class AITradeExplanation:
    symbol: str
    strategy_name: str
    title: str          # short title
    summary: str        # main explanation text
    risks: List[str]    # bullet list of risks
    notes: List[str]    # extra notes or suggestions

@dataclass
class AITradeReview:
    symbol: str
    strategy_name: str
    outcome: str        # "win" / "loss" / "breakeven"
    pnl: float
    lesson: str         # main lesson
    improvements: List[str]

🤖 4) LLM Client abstraction
ملف: sagetrade/ai/client.py
# FILE: sagetrade/ai/client.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()


class LLMClientBase(ABC):
    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: Optional[int] = None) -> str:
        ...


class MockLLMClient(LLMClientBase):
    """
    Placeholder backend that returns a simple deterministic message.
    Replace later with actual provider (OpenAI, etc.).
    """
    def generate(self, prompt: str, *, max_tokens: Optional[int] = None) -> str:
        logger.debug("mock_llm_generate event=mock_llm_call prompt_length=%d", len(prompt))
        return (
            "AI (mock) analysis:\n"
            "Based on the provided signal and risk parameters, this trade looks reasonable. "
            "Risk should remain controlled as long as stop-loss and position sizing rules are respected."
        )


def get_llm_client() -> LLMClientBase:
    """
    Factory to get an LLM client based on config.
    For now, always return MockLLMClient, but structure is ready for real backend.
    """
    ai_cfg = _settings.ai
    provider = getattr(ai_cfg, "provider", "mock")
    # مستقبلاً:
    # if provider == "openai": return OpenAILLMClient(...)
    # إلخ...
    logger.info("llm_client_init event=llm_client_init provider=%s model=%s", provider, ai_cfg.model)
    return MockLLMClient()


لاحقاً لما تحب تربطه بـ OpenAI أو غيره:

تضيف كلاس مثل OpenAILLMClient وتقرأ المفتاح من env.

🧠 5) AISignalAdvisor
ملف: sagetrade/ai/signal_advisor.py
# FILE: sagetrade/ai/signal_advisor.py

from __future__ import annotations
from textwrap import dedent

from sagetrade.ai.client import get_llm_client
from sagetrade.ai.models import AISignalAdvice
from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()
_llm = get_llm_client()


def build_signal_prompt(
    symbol: str,
    strategy_name: str,
    signal: CompositeSignal,
    risk: RiskState,
) -> str:
    """
    يبني prompt نصي يشرح للـ LLM وضع الصفقة المقترحة.
    """
    q = signal.quant
    nlp = signal.nlp
    social = signal.social

    nlp_part = (
        f"- News sentiment: {nlp.sentiment:.3f}, impact_score: {nlp.impact_score:.3f}, flags: {nlp.event_flags}\n"
        if nlp is not None else
        "- News sentiment: N/A\n"
    )

    social_part = (
        f"- Social sentiment: {social.sentiment:.3f}, buzz_score: {social.buzz_score:.3f}, volume_score: {social.volume_score:.3f}\n"
        if social is not None else
        "- Social sentiment: N/A\n"
    )

    prompt = dedent(f"""
    You are an AI trading risk advisor. You receive a proposed trade based on quantitative and news/social signals.

    Symbol: {symbol}
    Strategy: {strategy_name}

    Quant signals:
    - SMA: {q.sma:.4f}
    - EMA: {q.ema:.4f}
    - RSI: {q.rsi:.2f}
    - ATR: {q.atr:.4f}
    - Volatility: {q.volatility:.4f}
    - Regime: {q.regime}

    News / NLP:
    {nlp_part}
    Social:
    {social_part}

    Composite signal:
    - Direction: {signal.direction}
    - Score: {signal.score:.4f}
    - Confidence: {signal.confidence:.3f}

    Risk state:
    - Current equity: {risk.equity:.2f}
    - Start equity: {risk.equity_start:.2f}
    - Daily PnL: {risk.daily_pnl:.2f}
    - Open trades: {risk.open_trades}
    - Total open notional: {risk.total_open_notional:.2f}

    TASK:
    1. Briefly evaluate if entering this trade NOW is reasonable (approve, caution, or reject).
    2. If you think it's better to stay flat, indicate direction 'flat'.
    3. Optionally suggest adjusting the confidence (0..1).
    4. Explain your reasoning in 2-3 short sentences.

    Respond in concise English in the following JSON-like format (do NOT include backticks):

    decision: <approve|caution|reject>
    suggested_direction: <long|short|flat|none>
    suggested_confidence: <0.0-1.0 or 'none'>
    reason: <one or two sentences>
    """).strip()

    return prompt


def review_trade_candidate(
    symbol: str,
    strategy_name: str,
    signal: CompositeSignal,
    risk: RiskState,
) -> AISignalAdvice:
    """
    يستدعي LLM لمراجعة الصفقة المقترحة.
    لو فشل النداء → يرجع advice بسيط rule-based.
    """
    prompt = build_signal_prompt(symbol, strategy_name, signal, risk)

    try:
        raw = _llm.generate(prompt, max_tokens=_settings.ai.max_tokens)
        logger.debug(
            "ai_signal_advisor_response event=ai_signal_advisor_response symbol=%s strategy=%s raw=%s",
            symbol,
            strategy_name,
            raw,
        )
        # هنا نعمل parsing بسيط للخطوط (بدل JSON parser كامل في هذه المرحلة)
        decision = "approve"
        suggested_direction = None
        suggested_confidence = None
        reason = raw

        for line in raw.splitlines():
            line_lower = line.lower()
            if line_lower.startswith("decision:"):
                decision = line.split(":", 1)[1].strip()
            elif line_lower.startswith("suggested_direction:"):
                sd = line.split(":", 1)[1].strip()
                suggested_direction = None if sd in ("none", "") else sd
            elif line_lower.startswith("suggested_confidence:"):
                v = line.split(":", 1)[1].strip()
                if v.lower() in ("none", ""):
                    suggested_confidence = None
                else:
                    try:
                        suggested_confidence = float(v)
                    except ValueError:
                        suggested_confidence = None
            elif line_lower.startswith("reason:"):
                reason = line.split(":", 1)[1].strip()

        # ضمان صحة decision
        if decision not in ("approve", "caution", "reject"):
            decision = "approve"

        return AISignalAdvice(
            symbol=symbol,
            strategy_name=strategy_name,
            decision=decision, 
            reason=reason,
            suggested_direction=suggested_direction,
            suggested_confidence=suggested_confidence,
        )

    except Exception as exc:
        logger.error(
            "ai_signal_advisor_error event=ai_signal_advisor_error symbol=%s strategy=%s error=%s",
            symbol,
            strategy_name,
            exc,
        )
        # fallback rule-based بسيط
        fallback_reason = "AI unavailable; fallback rule-based approval."
        return AISignalAdvice(
            symbol=symbol,
            strategy_name=strategy_name,
            decision="approve",
            reason=fallback_reason,
        )


ثم داخل اللوب قبل إرسال order:

تستدعي review_trade_candidate(...)

ممكن تضيف منطق: لو decision="reject" → لا ترسل الصفقة.

📝 6) AITradeExplainer
ملف: sagetrade/ai/trade_explainer.py
# FILE: sagetrade/ai/trade_explainer.py

from __future__ import annotations
from textwrap import dedent

from sagetrade.ai.client import get_llm_client
from sagetrade.ai.models import AITradeExplanation
from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)
_llm = get_llm_client()


def _build_open_trade_prompt(
    symbol: str,
    strategy_name: str,
    side: str,
    qty: float,
    price: float,
    signal: CompositeSignal,
    risk: RiskState,
) -> str:
    q = signal.quant
    nlp = signal.nlp
    social = signal.social

    nlp_text = (
        f"News sentiment {nlp.sentiment:.3f} with impact {nlp.impact_score:.3f} and flags {nlp.event_flags}"
        if nlp is not None else "No specific news signal was available."
    )

    social_text = (
        f"Social sentiment {social.sentiment:.3f}, buzz {social.buzz_score:.3f}, volume_score {social.volume_score:.3f}"
        if social is not None else "No specific social signal was available."
    )

    prompt = dedent(f"""
    You are an AI trading assistant. Explain a newly opened trade in a concise, friendly way.

    Trade:
    - Symbol: {symbol}
    - Strategy: {strategy_name}
    - Side: {side}
    - Quantity: {qty:.4f}
    - Entry price: {price:.4f}

    Quant signals:
    - SMA: {q.sma:.4f}
    - EMA: {q.ema:.4f}
    - RSI: {q.rsi:.2f}
    - ATR: {q.atr:.4f}
    - Volatility: {q.volatility:.4f}
    - Regime: {q.regime}

    Composite signal:
    - Direction: {signal.direction}
    - Score: {signal.score:.4f}
    - Confidence: {signal.confidence:.3f}

    News / NLP: {nlp_text}
    Social: {social_text}

    Risk context:
    - Current equity: {risk.equity:.2f}
    - Start equity: {risk.equity_start:.2f}
    - Open trades: {risk.open_trades}
    - Total open notional: {risk.total_open_notional:.2f}

    TASK:
    1. Provide a short title summarizing the idea of the trade in one line.
    2. Provide a 3-5 sentence explanation aimed at a non-technical trader.
    3. List 2-4 key risks to monitor.
    4. Add 1-2 short notes or suggestions for managing the trade.

    Respond in a structured plain-text format (no JSON, no markdown):

    TITLE: <short title>
    SUMMARY: <one or two paragraphs>
    RISKS:
    - <risk 1>
    - <risk 2>
    NOTES:
    - <note 1>
    - <note 2>
    """).strip()

    return prompt


def explain_open_trade(
    symbol: str,
    strategy_name: str,
    side: str,
    qty: float,
    price: float,
    signal: CompositeSignal,
    risk: RiskState,
) -> AITradeExplanation:
    prompt = _build_open_trade_prompt(symbol, strategy_name, side, qty, price, signal, risk)

    try:
        raw = _llm.generate(prompt)
        logger.debug(
            "ai_trade_explainer_open event=ai_trade_explainer_open symbol=%s strategy=%s raw=%s",
            symbol,
            strategy_name,
            raw,
        )
        title = "New trade opened"
        summary = raw
        risks: list[str] = []
        notes: list[str] = []

        # parsing بسيط:
        current_section = None
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("TITLE:"):
                title = stripped.split(":", 1)[1].strip()
                current_section = None
            elif stripped.upper().startswith("SUMMARY:"):
                summary = stripped.split(":", 1)[1].strip()
                current_section = "SUMMARY"
            elif stripped.upper().startswith("RISKS:"):
                current_section = "RISKS"
            elif stripped.upper().startswith("NOTES:"):
                current_section = "NOTES"
            elif stripped.startswith("- "):
                item = stripped[2:].strip()
                if current_section == "RISKS":
                    risks.append(item)
                elif current_section == "NOTES":
                    notes.append(item)
            elif current_section == "SUMMARY":
                summary += " " + stripped

        return AITradeExplanation(
            symbol=symbol,
            strategy_name=strategy_name,
            title=title,
            summary=summary,
            risks=risks,
            notes=notes,
        )

    except Exception as exc:
        logger.error(
            "ai_trade_explainer_error event=ai_trade_explainer_error symbol=%s strategy=%s error=%s",
            symbol,
            strategy_name,
            exc,
        )
        return AITradeExplanation(
            symbol=symbol,
            strategy_name=strategy_name,
            title="New trade opened",
            summary="AI explanation not available; trade opened based on system rules and risk constraints.",
            risks=["Standard market volatility", "Unexpected news or events"],
            notes=["Monitor stop-loss levels", "Avoid over-leveraging"],
        )

📲 7) دمج AI مع Telegram bot
في config/settings.yaml نضيف:
ai:
  provider: "mock"        # أو "openai" لاحقاً
  model: "gpt-4.1-mini"   # اسم شكلي الآن
  max_tokens: 512
  language: "en"          # لاحقاً ممكن ar/en mix

في sagetrade/telegram/bot.py أو handlers.py

أفكار أوامر:

/explain_last:

تجيب آخر صفقة من broker

تجيب composite signal اللي فتحها (خزنه عند الفتح)

تستدعي explain_open_trade(...)

تبعث الـ summary + risks للمستخدم.

/ai_review:

على آخر إشارة/صفقة مرفوضة أو مقبولة

تستدعي review_trade_candidate(...)

ترجع decision + reason.

مثال Handler بسيط لأمر /explain_last
# FILE: sagetrade/telegram/handlers.py  (فكرة عامة)

from sagetrade.ai.trade_explainer import explain_open_trade
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

async def handle_explain_last(update, context):
    # pseudo-code:
    # 1) احضر آخر position من broker
    # 2) احضر composite signal المحفوظ وقت الدخول (تحتاج تخزنه في مكان ما)
    # هنا نضع هيكل تقريبي.
    chat_id = update.effective_chat.id
    broker = context.bot_data["broker"]
    risk_state = context.bot_data["risk_state"]

    last_pos = broker.get_last_open_or_closed_position()
    if last_pos is None:
        await context.bot.send_message(chat_id=chat_id, text="لا توجد صفقات لشرحها حالياً.")
        return

    symbol = last_pos.symbol
    strategy_name = last_pos.strategy_name
    side = last_pos.side
    qty = last_pos.qty
    price = last_pos.entry_price

    # composite_at_entry تحتاج تخزينها في وقت فتح الصفقة؛
    # هنا نفترض أنك تحفظها في dict داخل broker أو engine
    composite = last_pos.meta.get("composite_signal")

    if composite is None:
        await context.bot.send_message(chat_id=chat_id, text="لا يوجد سياق كامل للصفقة، لكن سأحاول الشرح لاحقاً.")
        return

    expl = explain_open_trade(symbol, strategy_name, side, qty, price, composite, risk_state)
    text = (
        f"**{expl.title}**\n\n"
        f"{expl.summary}\n\n"
        f"*Risks:*\n" + "\n".join(f"- {r}" for r in expl.risks) +
        "\n\n*Notes:*\n" + "\n".join(f"- {n}" for n in expl.notes)
    )

    # لو البوت يدعم Markdown:
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


المهم هنا: أنت تجهز الـ plumbing. تفاصيل التخزين (meta["composite_signal"]) نقدر نضبطها في مرحلة لاحقة.

🧾 8) ما الذي يجب أن يكون جاهزًا بعد Part 9؟

إعدادات AI في settings.yaml (قسم ai)

ملفات جديدة:

sagetrade/ai/models.py

sagetrade/ai/client.py

sagetrade/ai/signal_advisor.py

sagetrade/ai/trade_explainer.py

AISignalAdvisor جاهز يراجع أي صفقة قبل التنفيذ (حتى لو حالياً mock LLM)

AITradeExplainer جاهز يعطي نص شرح (يستخدم في Telegram و logs)

تلغرام فيه على الأقل أمر واحد يستخدم AI (مثل /explain_last)

في الـ trading loop:

صار فيه خطوة إضافية اختيارية: سؤال الـ AISignalAdvisor قبل إرسال order.

🤖 9) Prompt جاهز تعطيه لـ AI Agent لينفّذ Part 9

انسخ هذا الـ prompt وأرسله للو agent اللي يشتغل على الريبو:

You are a senior Python engineer and ML integration specialist working on my trading project SAGE SmartTrade.

CONTEXT:
- The project has:
  - CompositeSignal + strategies + RiskManager + trading loop.
  - A Telegram bot skeleton.
  - A config system using settings.yaml and Pydantic models.
- I now want to implement Phase 9: AI layer for signal review and trade explanations.

TASK:

1) Extend `config/settings.yaml` to include an `ai` section with fields:
   - provider (e.g. "mock" for now)
   - model (string)
   - max_tokens (int)
   - language (string, e.g. "en")

2) Create `sagetrade/ai/models.py` with dataclasses:
   - `AISignalAdvice`:
     - symbol: str
     - strategy_name: str
     - decision: Literal["approve", "caution", "reject"]
     - reason: str
     - suggested_direction: Optional[str]
     - suggested_confidence: Optional[float]
   - `AITradeExplanation`:
     - symbol: str
     - strategy_name: str
     - title: str
     - summary: str
     - risks: list[str]
     - notes: list[str]
   - `AITradeReview` (optional for future):
     - symbol: str
     - strategy_name: str
     - outcome: str
     - pnl: float
     - lesson: str
     - improvements: list[str]

3) Create `sagetrade/ai/client.py`:
   - Define abstract `LLMClientBase` with `generate(prompt: str, max_tokens: Optional[int] = None) -> str`.
   - Implement `MockLLMClient` that logs the call and returns a simple deterministic analysis string.
   - Implement `get_llm_client()` factory that reads `settings.ai.provider` and returns `MockLLMClient` for now.

4) Implement `sagetrade/ai/signal_advisor.py`:
   - A function `build_signal_prompt(symbol, strategy_name, signal: CompositeSignal, risk: RiskState) -> str`
     that assembles a detailed prompt with:
       - quant metrics (sma, ema, rsi, atr, volatility, regime)
       - news/nlp (sentiment, impact_score, flags) if available
       - social signals if available
       - composite direction, score, confidence
       - risk context (equity, equity_start, daily_pnl, open_trades, total_open_notional)
   - A function `review_trade_candidate(symbol, strategy_name, signal, risk) -> AISignalAdvice` that:
     - calls the LLM client with the prompt.
     - expects a structured plain-text response like:
       decision: <approve|caution|reject>
       suggested_direction: <long|short|flat|none>
       suggested_confidence: <0.0-1.0 or 'none'>
       reason: <...>
     - parses these lines into an `AISignalAdvice` instance.
     - on error, logs and returns a fallback `AISignalAdvice` with decision="approve" and a generic reason.

5) Implement `sagetrade/ai/trade_explainer.py`:
   - A helper `_build_open_trade_prompt(symbol, strategy_name, side, qty, price, signal: CompositeSignal, risk: RiskState) -> str`
     that describes the trade, quant & NLP signals, and risk context.
   - A function `explain_open_trade(symbol, strategy_name, side, qty, price, signal, risk) -> AITradeExplanation` that:
     - calls the LLM with a prompt instructing it to respond in this format:

       TITLE: <short title>
       SUMMARY: <one or two paragraphs>
       RISKS:
       - <risk 1>
       - <risk 2>
       NOTES:
       - <note 1>
       - <note 2>

     - parses the response into an `AITradeExplanation`.
     - on error, logs and returns a fallback explanation with generic content.

6) Integrate AISignalAdvisor into the main trading loop (e.g. `scripts/paper_trade_loop.py`):
   - After a strategy decides to enter and before submitting an order:
     - call `review_trade_candidate(symbol, strat.name, composite, risk_state)`.
     - log the AI decision and reason.
     - optionally, if decision == "reject", skip submitting the order.
     - optionally, if `suggested_direction` and `suggested_confidence` are provided, adjust the signal or just log them for now.

7) Integrate AITradeExplainer with Telegram (in `sagetrade/telegram/handlers.py` or equivalent):
   - Add a handler for a command like `/explain_last` that:
     - fetches the last trade (open or recently closed) from the broker or engine.
     - retrieves the stored CompositeSignal at entry time (from a `meta` field or similar).
     - calls `explain_open_trade(...)`.
     - sends the explanation (title, summary, risks, notes) to the user (Markdown or plain text).
   - Ensure errors are handled gracefully and logged.

STYLE:
- Use Python 3.11+ typing and dataclasses.
- Use existing config (`get_settings`) and logging helpers.
- Keep LLM integration abstract (no direct vendor-specific SDK code for now).
- Output all changes as code blocks with file paths, e.g.:

  # FILE: config/settings.yaml
  ...
  # FILE: sagetrade/ai/models.py
  ...
  # FILE: sagetrade/ai/client.py
  ...
  # FILE: sagetrade/ai/signal_advisor.py
  ...
  # FILE: sagetrade/ai/trade_explainer.py
  ...
  # FILE: sagetrade/telegram/handlers.py
  ...
  # FILE: scripts/paper_trade_loop.py
  ...
