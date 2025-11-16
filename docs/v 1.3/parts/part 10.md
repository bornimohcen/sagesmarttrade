Part 10 = ضبط شخصية الـ AI + UX التيليغرام
هنا نخلي البوت لطيف، ذكي، ومفهوم بدل ما يكون مجرد لوجات مملة 😄

رح أقسم Part 10 كذا:

الهدف من الجزء 10

تحسين الـ Prompts للـ AI (قبل الصفقة، بعد الصفقة، مراجعة المخاطر)

دعم لغتين (عربي + إنجليزي) بأسلوب متّسق

تصميم UX لبوت التيليغرام (الأوامر + الأزرار + الردود)

ربط Telegram مع AI layer (explain, review, alerts)

Prompt جاهز تعطيه لـ AI Agent يعدّل الكود والـ Prompts

1️⃣ هدف Part 10

الآن عندك:

Engine تداول + RiskManager + Strategies + CompositeSignal ✅

طبقة AI (SignalAdvisor + TradeExplainer) بشكل أوّلي ✅

في Part 10 نريد:

Prompts احترافية للـ AI:

قبل الصفقة (AI يراجعها)

بعد فتح الصفقة (AI يشرحها)

بعد إغلاق الصفقة (AI يراجعها ويعطي دروس)

Alerts للمخاطر (مثلاً يوم خاسر بقوّة أو drawdown عالي)

Telegram UX:

أوامر واضحة

ردود مرتبة ومختصرة

أزرار Inline (مثلاً “اشرح الصفقة الأخيرة”، “أظهر الصفقات المفتوحة”)

دمج الردود مع AI (مو بس أرقام جامدة)

2️⃣ تحسين الـ Prompts للـ AI
🧠 2.1 — Prompt محسّن لـ AISignalAdvisor (قبل الصفقة)

في Part 9 عملنا Prompt أساسي. الآن نصممه أوضح، مع أسلوب ثابت، + إمكانية لغة مزدوجة.

فكرة:

نحدد “شخصية” الـ AI:

هادئ، محافظ، يهمّه إدارة المخاطر

نحدد شكل الردّ بدقة (decision + reasoning + suggestions)

Template جديد (تضعه في build_signal_prompt بدل القديم):
You are "SAGE-RISK-AI", an experienced trading risk advisor.
Your style:
- Conservative and risk-aware.
- Clear, concise, and non-hype.
- You never encourage over-leverage or revenge trading.

You receive a proposed trade based on quantitative and news/social signals.

TRADE CONTEXT:
- Symbol: {symbol}
- Strategy: {strategy_name}

QUANT SIGNALS:
- SMA: {q.sma:.4f}
- EMA: {q.ema:.4f}
- RSI: {q.rsi:.2f}
- ATR: {q.atr:.4f}
- Volatility: {q.volatility:.4f}
- Regime: {q.regime}

NEWS / NLP:
{nlp_part}

SOCIAL:
{social_part}

COMPOSITE SIGNAL:
- Direction: {signal.direction}
- Score: {signal.score:.4f} (range approx -1.0 to +1.0)
- Confidence: {signal.confidence:.3f} (0 = low, 1 = very high)

RISK STATE:
- Current equity: {risk.equity:.2f}
- Start equity: {risk.equity_start:.2f}
- Daily PnL: {risk.daily_pnl:.2f}
- Open trades: {risk.open_trades}
- Total open notional: {risk.total_open_notional:.2f}

TASK:
1. Evaluate if entering this trade NOW is reasonable from a risk perspective.
2. Choose one decision:
   - "approve" → trade looks acceptable.
   - "caution" → trade is acceptable but with warnings.
   - "reject" → better to stay flat now.
3. Optionally suggest a better direction: long, short, or flat.
4. Optionally suggest an adjusted confidence between 0 and 1.
5. Explain your reasoning in 2–3 short sentences.

IMPORTANT:
- Focus on risk, not hype.
- If daily PnL is already strongly negative or exposure is high, lean towards "caution" or "reject".

RESPONSE FORMAT (plain text, no JSON, no backticks):

decision: <approve|caution|reject>
suggested_direction: <long|short|flat|none>
suggested_confidence: <0.0-1.0 or 'none'>
reason: <2-3 sentences explanation>


تقدر تضيف ملاحظة: “if language setting is 'ar', add a short Arabic summary in one sentence at the end.”

🧠 2.2 — Prompt محسّن لـ Trade Explainer (بعد فتح الصفقة)

بدل كلام عام، نُضيف:

سبب الدخول

دور الاستراتيجية

كيف نراقب الصفقة

Template جديد لـ _build_open_trade_prompt:

You are "SAGE-EXPLAIN-AI", an AI trading assistant.
Your task is to explain a newly opened trade to a human trader who understands basics but is not a quant expert.

TRADE:
- Symbol: {symbol}
- Strategy: {strategy_name}
- Side: {side} (long = buy expecting price up, short = sell expecting price down)
- Quantity: {qty:.4f}
- Entry price: {price:.4f}

QUANT SIGNALS (last window):
- SMA: {q.sma:.4f}
- EMA: {q.ema:.4f}
- RSI: {q.rsi:.2f}
- ATR: {q.atr:.4f}
- Volatility: {q.volatility:.4f}
- Regime: {q.regime}

COMPOSITE SIGNAL:
- Direction: {signal.direction}
- Score: {signal.score:.4f}
- Confidence: {signal.confidence:.3f}

NEWS / NLP:
{nlp_text}

SOCIAL:
{social_text}

RISK CONTEXT:
- Current equity: {risk.equity:.2f}
- Start equity: {risk.equity_start:.2f}
- Open trades: {risk.open_trades}
- Total open notional: {risk.total_open_notional:.2f}

TASK:
1. Provide a short title summarizing the idea of the trade in ONE line.
2. Provide a 3–5 sentence explanation of:
   - Why the system entered this trade now.
   - How the quantitative and news/social signals support the idea.
   - How aggressive or conservative the trade is.
3. Give 2–4 key risks to monitor (in bullet points).
4. Give 1–3 short notes or suggestions for managing the trade (e.g., what to watch, when to reduce risk).

LANGUAGE:
- Write in English, but add ONE short Arabic sentence at the end of SUMMARY summarizing the idea.

RESPONSE FORMAT (plain text, no JSON, no markdown):

TITLE: <short title>
SUMMARY: <one or two paragraphs including the Arabic sentence at the end>
RISKS:
- <risk 1>
- <risk 2>
- <risk 3>
NOTES:
- <note 1>
- <note 2>
- <note 3>


كذا تحصل Explanation حلوة + فيها جملة عربية بسيطة تعطي روح للبوت.

🧠 2.3 — Prompt لمراجعة الصفقة بعد الإغلاق (Post-Trade Review)

هذا ممكن تحطه في ملف جديد ai/trade_reviewer.py أو تضيفه في المستقبل.

Template:

You are "SAGE-REVIEW-AI", an AI trading mentor.
You will review a completed trade and extract lessons.

TRADE SUMMARY:
- Symbol: {symbol}
- Strategy: {strategy_name}
- Side: {side}
- Entry price: {entry_price:.4f}
- Exit price: {exit_price:.4f}
- Quantity: {qty:.4f}
- Realized PnL: {pnl:.2f}
- Holding period: {holding_period_minutes} minutes

ENTRY SIGNAL SNAPSHOT:
- Composite direction at entry: {entry_signal.direction}
- Score: {entry_signal.score:.4f}
- Confidence: {entry_signal.confidence:.3f}
- Quant regime: {entry_signal.quant.regime}
- RSI at entry: {entry_signal.quant.rsi:.2f}

RISK CONTEXT AT ENTRY:
- Equity: {entry_risk_equity:.2f}
- Open trades: {entry_open_trades}

TASK:
1. Classify the outcome as win, loss, or breakeven.
2. Give a 2–4 sentence review explaining what went right or wrong.
3. Provide 2–4 concrete improvements (rules, filters, or risk tweaks) that could help similar trades in the future.
4. Keep the tone calm, objective, and educational.

RESPONSE FORMAT:

OUTCOME: <win|loss|breakeven>
LESSON: <one paragraph with the main lesson>
IMPROVEMENTS:
- <improvement 1>
- <improvement 2>
- <improvement 3>

3️⃣ دعم لغتين (عربي + إنجليزي)

بدل ما تغيّر كل مرّة، خلّي في settings:

ai:
  language: "mix"   # options: "en", "ar", "mix"


وفي الـ prompts:

إذا language == "en" → كل النص إنجليزي

إذا language == "ar" → تطلب من الـ AI يشرح بالعربية، ويضيف مصطلحات إنجليزية عند الحاجة

إذا mix → زي ما فوق: إنجليزي أساسي + جملة عربية اختصار في النهاية

تقدر تعدل في build_signal_prompt و _build_open_trade_prompt:

تضيف شرط بسيط:

لو اللغة "ar":

تضيف في الـ TASK: “Use Modern Standard Arabic as the main language, with English terms for technical indicators (RSI, EMA, ATR...).”

4️⃣ تصميم UX لبوت التيليغرام

خلي البوت يعطيك:

أوامر رئيسية:

/start

يرسل رسالة ترحيب + قائمة أوامر

/status

ملخّص سريع:

equity

daily PnL

open trades

last trade

/open

قائمة الصفقات المفتوحة (symbol, side, entry, PnL%)

/closed

آخر N صفقات مغلقة

/signals

آخر CompositeSignal لكل رمز

/ai_review

رأي AISignalAdvisor في آخر صفقة / إشارة

/explain_last

يستخدم AITradeExplainer لشرح آخر صفقة

/risk

ملخص حدود المخاطر (max_risk_per_trade_pct, max_daily_loss_pct, ...)

أزرار Inline (InlineKeyboard)

مثال:

بعد فتح صفقة، البوت يرسل:

تم فتح صفقة جديدة على BTCUSD (short @ 40,000, حجم 0.01).

مع أزرار:

🔍 شرح الصفقة (AI) → يرسل نتيجة explain_open_trade

📊 وضع الحساب → ينفّذ /status

🧠 رأي AI في الإشارة → يرسل آخر AISignalAdvice

تقدر في python-telegram-bot تستخدم:

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [
        InlineKeyboardButton("🔍 شرح الصفقة (AI)", callback_data="explain_last"),
        InlineKeyboardButton("📊 وضع الحساب", callback_data="status"),
    ],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup)


وفي handler لـ callback_data:

لو "explain_last" → تستدعي explain_open_trade وترسل

لو "status" → ترسل /status info

5️⃣ ربط Telegram مع AI layer (بشكل عملي)
مثال: عند فتح صفقة في trading loop

بعد:

order = broker.submit_order(...)
position = broker.get_position(order.id)


تعمل:

from sagetrade.ai.trade_explainer import explain_open_trade
from sagetrade.telegram.notify import notify_new_trade

# احفظ composite في position.meta مثلاً
position.meta["composite_signal"] = composite
position.meta["strategy_name"] = strat.name

# AI explanation (اختياري في background, لكن عندنا لازم الآن مباشرة)
expl = explain_open_trade(
    symbol=symbol,
    strategy_name=strat.name,
    side=side,
    qty=qty,
    price=price,
    signal=composite,
    risk=risk_state,
)

# إرسال لتيليغرام:
notify_new_trade(position, expl)


وفي notify_new_trade تبني رسالة لطيفة:

def notify_new_trade(position, expl: AITradeExplanation):
    text = (
        f"🚨 *صفقة جديدة*\n"
        f"رمز: `{position.symbol}`\n"
        f"الاستراتيجية: *{expl.strategy_name}*\n"
        f"الاتجاه: *{position.side.upper()}*\n"
        f"السعر: `{position.entry_price:.4f}`\n"
        f"الكمية: `{position.qty:.4f}`\n\n"
        f"*{expl.title}*\n"
        f"{expl.summary}\n\n"
        f"*المخاطر:*\n" + "\n".join(f"- {r}" for r in expl.risks)
    )
    # + InlineKeyboardMarkup للأزرار

6️⃣ Prompt جاهز لـ AI Agent لتنفيذ Part 10

انسخ النص هذا كما هو لوكيل AI اللي شغال على الريبو:

You are a senior Python developer and prompt engineer working on my project SAGE SmartTrade.

CONTEXT:
- The project now has:
  - CompositeSignal, strategies, RiskManager, trading loop.
  - AI layer with AISignalAdvisor and AITradeExplainer (Phase 9).
  - A Telegram bot skeleton.
- I want to improve both:
  - AI prompts (quality & style)
  - Telegram UX (commands, inline buttons, AI-powered replies)

TASK:

1) Improve the prompt used in `sagetrade/ai/signal_advisor.py` (build_signal_prompt):
   - Define the persona "SAGE-RISK-AI":
     - Conservative, risk-aware, no hype.
   - Include clear instructions:
     - Focus on risk, daily PnL, exposure, and confidence.
     - Bias towards "caution" or "reject" when daily losses or exposure are high.
   - Require the response format:

     decision: <approve|caution|reject>
     suggested_direction: <long|short|flat|none>
     suggested_confidence: <0.0-1.0 or 'none'>
     reason: <2-3 sentences explanation>

   - Integrate `settings.ai.language` with options "en", "ar", "mix":
     - For "en": English only.
     - For "ar": Modern Standard Arabic with English technical terms.
     - For "mix": English main text + one short Arabic sentence summarizing the idea.

2) Improve the prompt in `sagetrade/ai/trade_explainer.py` (_build_open_trade_prompt):
   - Define persona "SAGE-EXPLAIN-AI":
     - Friendly, clear, and non-technical.
   - Require response format:

     TITLE: <short title>
     SUMMARY: <one or two paragraphs>
     RISKS:
     - <risk 1>
     - <risk 2>
     NOTES:
     - <note 1>
     - <note 2>

   - For language "mix":
     - Add ONE short Arabic sentence at the end of SUMMARY summarizing the idea.

3) Optionally add a new module `sagetrade/ai/trade_reviewer.py`:
   - Define a function that takes:
     - trade data (entry, exit, pnl, holding period)
     - entry CompositeSignal and risk context
   - Builds a prompt for "SAGE-REVIEW-AI" with response format:

     OUTCOME: <win|loss|breakeven>
     LESSON: <one paragraph>
     IMPROVEMENTS:
     - <improvement 1>
     - <improvement 2>

4) Telegram UX:
   - In `sagetrade/telegram` (e.g. handlers.py or bot.py), implement:
     - Commands:
       - `/status`: send current equity, daily PnL, open trades count, last trade.
       - `/open`: list open positions (symbol, side, entry, unrealized PnL).
       - `/closed`: list last N closed trades (symbol, side, PnL).
       - `/signals`: list latest CompositeSignal per symbol (direction, score, confidence).
       - `/ai_review`: show latest AISignalAdvice (decision + reason).
       - `/explain_last`: call AITradeExplainer on the last trade and send the explanation.
   - Implement inline buttons for a new trade notification:
     - "🔍 شرح الصفقة (AI)" → triggers the same logic as `/explain_last`.
     - "📊 وضع الحساب" → triggers the same logic as `/status`.

5) Integration:
   - In the trading loop:
     - After a trade is opened and a `CompositeSignal` is available:
       - store the composite signal and strategy name inside the position metadata.
       - call `explain_open_trade(...)` to generate an AI explanation.
       - pass both the position and explanation into a Telegram notifier helper (e.g. `notify_new_trade`).
   - In Telegram handlers:
     - Implement `/explain_last` and the inline callback "explain_last" to:
       - fetch the last position.
       - retrieve the stored CompositeSignal.
       - call `explain_open_trade(...)` if explanation not already cached.
       - send a nicely formatted message (Markdown) with title, summary, risks, notes.

STYLE:
- Keep prompts in clear multiline strings using `dedent`.
- Respect `settings.ai.language` when generating prompts.
- Use existing logging and config utilities.
- Output updated files as code blocks with paths, for example:

  # FILE: sagetrade/ai/signal_advisor.py
  ...
  # FILE: sagetrade/ai/trade_explainer.py
  ...
  # FILE: sagetrade/ai/trade_reviewer.py
  ...
  # FILE: sagetrade/telegram/handlers.py
  ...
  # FILE: scripts/paper_trade_loop.py
  ...
