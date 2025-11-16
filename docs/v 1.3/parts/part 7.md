Part 7: Signals Engine (Quant + NLP + Social + Composite)
هذا هو “مخه” الحقيقي للبوت – المكان اللي منه يطلع:
اتجاه، درجة ثقة، سبب، وحدّة المخاطر.

أنا سأقسم لك Part 7 كالتالي:

الفكرة العامة: كيف نريد نظام الإشارات يشتغل

تقسيم المرحلة لمهام تفصيلية

تصميم الـ dataclasses (Quant, News/NLP, Social, Composite)

منطق حساب QuantSignals (من OHLCV)

Placeholder منطقي لـ NLP & Social لحد ما نربطها بالـ ingestion

منطق بناء CompositeSignal (وزن لكل نوع) + direction + confidence

كيف ندمج signals داخل الـ trading loop

Prompt جاهز طويل تعطيه لـ AI Agent ينفّذ لك هذه المرحلة في المشروع

🧠 1) ما الذي نريده من Signals Engine؟

نريد pipeline واضح:

عندنا بيانات سعرية (OHLCV) لـ symbol معين → نحسب منها:

SMA / EMA

RSI

ATR

Volatility

Regime (high_vol / low_vol / trending / ranging)
⇒ هذا يصبح QuantSignals

عندنا نصوص أخبار + عناوين + ربما وصف من social → نطلع منها:

sentiment (من -1 إلى 1)

event_flags (earnings, guidance, downgrade, فجوة سعرية، إلخ)

impact_score (0 → 1)

language
⇒ هذا يصبح NLPNewsSignals أو NLPSignals

عندنا بيانات تفاعل Social:

Post sentiment average

حجم التفاعل (likes, retweets, upvotes)

hype score
⇒ هذا يصبح SocialSignals

هذه الثلاثة تُدمج مع تقييم AI (AISignalAdvisor) في:

CompositeSignal

يحتوي:

symbol

quant

nlp

social

ai (اختياري الآن)

score (نهائي)

direction (long, short, flat)

confidence (0→1)

هذا الكائن CompositeSignal هو ما يراه:

StrategyManager

RiskManager (عبر AI risk لاحقاً)

Telegram bot عند الشرح

🧩 2) تقسيم Part 7 إلى مهام
🧱 7.1 — تصميم الـ dataclasses للإشارات

ملف: sagetrade/signals/quant.py, nlp_news.py, social.py, composite.py

نريد:

QuantSignals

NLPNewsSignals (أو NLPSignals لو حاب تختصر)

SocialSignals

CompositeSignal

🧱 7.2 — كتابة دوال لحساب QuantSignals من سلسلة OHLCV

مدخل: list / pandas DataFrame من:

timestamp, open, high, low, close, volume

مخرجات:

sma

ema

rsi

atr

volatility (std dev)

regime (من قواعد بسيطة)

🧱 7.3 — إعداد واجهات حساب NLP و Social (حتى لو حالياً dummy)

إلى أن نربط ingestion الحقيقي:

نكتب Functions ترجع signals مع قيم افتراضية معقولة:

sentiment = 0.0

impact_score = 0.0

event_flags = {}
أو تعتمد على mock data من ملفات نصوص.

المهم: الشكل ثابت، ويمكن لاحقاً استبدال implementation.

🧱 7.4 — منطق CompositeSignal (scoring + direction)

نحتاج:

وزن لكل نوع:

quant_weight

news_weight

social_weight

ai_weight (حتى لو مستقبلاً)

طريقة لحساب score نهائي:

linear combination (سهل في البداية)

طريقة لتحويل score إلى اتجاه:

score > +threshold → "long"

score < -threshold → "short"

بينهما → "flat"

confidence:

مثلاً = |score| مقسومة على max_score مع قص (clamp) عند 1.0

🧱 7.5 — إدخال Signals في الـ trading loop

في كل دورة:

لرمز معيّن:

حمّل آخر window من الأسعار

احسب QuantSignals

احسب NLPNewsSignals (من النصوص الحديثة)

احسب SocialSignals (من postات حديثة)

استدع AI advisor لو جاهز

كوّن CompositeSignal

مرر CompositeSignal إلى الاستراتيجيات:

strategy.should_enter(composite, risk_state)

سجّل log واضح لـ CompositeSignal.

🧱 3) تصميم dataclasses للإشارات
📄 QuantSignals
# FILE: sagetrade/signals/quant.py

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class QuantSignals:
    symbol: str
    window: int
    sma: float
    ema: float
    rsi: float
    atr: float
    volatility: float
    regime: str  # e.g. "high_vol", "low_vol", "trending_up", "trending_down"

📄 NLPNewsSignals
# FILE: sagetrade/signals/nlp_news.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class NLPNewsSignals:
    entity: str              # could be symbol or 'market'
    sentiment: float         # -1 .. 1
    impact_score: float      # 0 .. 1
    event_flags: Dict[str, bool] = field(default_factory=dict)
    language: str = "en"

📄 SocialSignals
# FILE: sagetrade/signals/social.py

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SocialSignals:
    symbol: str
    sentiment: float         # -1 .. 1
    buzz_score: float        # 0 .. 1 (intensity of mentions/engagement)
    volume_score: float      # 0 .. 1 (relative to history)

📄 CompositeSignal
# FILE: sagetrade/signals/composite.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from sagetrade.signals.quant import QuantSignals
from sagetrade.signals.nlp_news import NLPNewsSignals
from sagetrade.signals.social import SocialSignals

@dataclass
class CompositeSignal:
    symbol: str
    quant: QuantSignals
    nlp: Optional[NLPNewsSignals] = None
    social: Optional[SocialSignals] = None

    score: float = 0.0         # final numeric score
    direction: str = "flat"    # "long", "short", "flat"
    confidence: float = 0.0    # 0 .. 1


لو حاب تضيف حقل ai بعدين (AISignalAdvisor): سهل.

🧱 4) منطق حساب QuantSignals من OHLCV

نفترض عندك بيانات في DataFrame (pandas)، مثلًا:
df يحتوي columns: "open","high","low","close","volume" مع index = timestamp.

📄 دوال المساعدة في quant.py
# FILE: sagetrade/signals/quant.py  (add below dataclass)

import numpy as np
import pandas as pd

def _ema(series: pd.Series, span: int) -> float:
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])

def _sma(series: pd.Series, window: int) -> float:
    return float(series.rolling(window=window).mean().iloc[-1])

def _rsi(series: pd.Series, window: int) -> float:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(window=window).mean()
    roll_down = down.rolling(window=window).mean()
    rs = roll_up / (roll_down + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> float:
    prev_close = close.shift(1)
    tr = np.maximum(high - low, np.maximum((high - prev_close).abs(), (low - prev_close).abs()))
    atr = tr.rolling(window=window).mean()
    return float(atr.iloc[-1])

def _volatility(series: pd.Series, window: int) -> float:
    return float(series.pct_change().rolling(window=window).std().iloc[-1])

def _detect_regime(close: pd.Series, window: int) -> str:
    vol = _volatility(close, window)
    # هذا منطق بسيط، تقدر تحسّنه لاحقًا
    if vol > 0.03:
        return "high_vol"
    elif vol < 0.01:
        return "low_vol"
    else:
        return "normal"

def compute_quant_signals(symbol: str, df: pd.DataFrame, window: int = 20) -> QuantSignals:
    if len(df) < window + 1:
        raise ValueError(f"Not enough data for {symbol}: need {window+1}, got {len(df)}")

    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = _sma(close, window)
    ema = _ema(close, window)
    rsi = _rsi(close, window)
    atr = _atr(high, low, close, window)
    vol = _volatility(close, window)
    regime = _detect_regime(close, window)

    return QuantSignals(
        symbol=symbol,
        window=window,
        sma=sma,
        ema=ema,
        rsi=rsi,
        atr=atr,
        volatility=vol,
        regime=regime,
    )

🧱 5) Placeholder لـ NLP & Social Signals

حتى نربط لاحقاً مع ingestion و AI، نضع Functions بسيطة ترجع قيم مقبولة:

📄 nlp_news.py
# FILE: sagetrade/signals/nlp_news.py  (add below dataclass)

from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

def compute_nlp_news_signals(entity: str) -> NLPNewsSignals:
    """
    Placeholder for now. Later this will:
      - fetch recent news texts
      - run sentiment / event extraction
    """
    # حاليا نضع قيم افتراضية = محايدة
    sentiment = 0.0
    impact_score = 0.0
    event_flags = {"earnings": False, "ma": False, "guidance": False}

    logger.debug(
        "nlp_news_signals_placeholder event=nlp_news_signals entity=%s sentiment=%.3f impact=%.3f",
        entity,
        sentiment,
        impact_score,
    )

    return NLPNewsSignals(
        entity=entity,
        sentiment=sentiment,
        impact_score=impact_score,
        event_flags=event_flags,
        language="en",
    )

📄 social.py
# FILE: sagetrade/signals/social.py  (add below dataclass)

from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

def compute_social_signals(symbol: str) -> SocialSignals:
    """
    Placeholder for now. Later this will:
      - fetch social posts
      - compute sentiment & buzz
    """
    sentiment = 0.0
    buzz_score = 0.0
    volume_score = 0.0

    logger.debug(
        "social_signals_placeholder event=social_signals symbol=%s sentiment=%.3f buzz=%.3f volume=%.3f",
        symbol,
        sentiment,
        buzz_score,
        volume_score,
    )

    return SocialSignals(
        symbol=symbol,
        sentiment=sentiment,
        buzz_score=buzz_score,
        volume_score=volume_score,
    )

🧱 6) منطق CompositeSignal (score + direction + confidence)

في composite.py نضيف دالة:

# FILE: sagetrade/signals/composite.py  (extend file)

from sagetrade.utils.logging import get_logger
from sagetrade.signals.quant import QuantSignals
from sagetrade.signals.nlp_news import NLPNewsSignals
from sagetrade.signals.social import SocialSignals

logger = get_logger(__name__)

def build_composite_signal(
    symbol: str,
    quant: QuantSignals,
    nlp: NLPNewsSignals | None = None,
    social: SocialSignals | None = None,
    *,
    quant_weight: float = 0.5,
    news_weight: float = 0.3,
    social_weight: float = 0.2,
    threshold: float = 0.01,
) -> CompositeSignal:
    """
    Build a CompositeSignal from its components.
    score in [-1, 1], where:
      >0 = bullish, <0 = bearish.
    """

    # 1) Quant score (مثال بسيط: based on close vs sma + rsi)
    # لاحقاً تقدر تحسنه
    quant_score = 0.0
    # لو السعر فوق الـ SMA و RSI في منطقة صعود
    # (هذا مثال تقريبي، انت حر تصممه كما تحب)
    # نقدر نقدر الاتجاه من EMA - SMA، أو من RSI
    rsi_norm = (quant.rsi - 50.0) / 50.0  # من -1..1 تقريبا
    quant_score += 0.6 * rsi_norm

    # 2) News score
    news_score = 0.0
    if nlp is not None:
        news_score = nlp.sentiment * nlp.impact_score  # تأثير مضروب في أهمية الخبر

    # 3) Social score
    social_score = 0.0
    if social is not None:
        social_score = social.sentiment * max(social.buzz_score, 0.1)

    # 4) combine
    raw_score = (
        quant_weight * quant_score +
        news_weight * news_score +
        social_weight * social_score
    )

    # Clip score بين -1 و 1
    score = max(min(raw_score, 1.0), -1.0)

    # 5) determine direction
    if score > threshold:
        direction = "long"
    elif score < -threshold:
        direction = "short"
    else:
        direction = "flat"

    # 6) confidence = |score|
    confidence = abs(score)

    composite = CompositeSignal(
        symbol=symbol,
        quant=quant,
        nlp=nlp,
        social=social,
        score=score,
        direction=direction,
        confidence=confidence,
    )

    logger.info(
        "composite_signal event=composite_signal symbol=%s direction=%s score=%.4f conf=%.3f regime=%s rsi=%.2f",
        symbol,
        direction,
        score,
        confidence,
        quant.regime,
        quant.rsi,
    )

    return composite


المنطق هنا مبسط لكنه:

يعطيك score في [-1,1]

يعطي direction

يعطي confidence

وتقدر تعدّله/تطوّره لاحقًا براحتك.

🧱 7) إدماج Signals في الـ trading loop

في سكريبت اللوب (مثل scripts/paper_trade_loop.py في مشروعك):

بعد تحميل الأسعار لرمز معيّن (df):

from sagetrade.signals.quant import compute_quant_signals
from sagetrade.signals.nlp_news import compute_nlp_news_signals
from sagetrade.signals.social import compute_social_signals
from sagetrade.signals.composite import build_composite_signal

def process_symbol(symbol: str, df: pd.DataFrame):
    quant = compute_quant_signals(symbol, df, window=20)
    nlp = compute_nlp_news_signals(entity=symbol)      # أو "market" حسب تصميمك
    social = compute_social_signals(symbol=symbol)

    composite = build_composite_signal(
        symbol=symbol,
        quant=quant,
        nlp=nlp,
        social=social,
    )

    return composite


داخل اللوب الأساسي:

for symbol in symbols:
    df = load_recent_bars(symbol)  # دالة موجودة عندك أو ستبنيها
    if df is None:
        logger.warning("[%s] no bars found; skipping.", symbol)
        continue

    composite = process_symbol(symbol, df)

    # مرر composite إلى الاستراتيجيات:
    for strategy in strategies:
        if not strategy.is_enabled_for(symbol):
            continue
        decision = strategy.should_enter(composite, risk_state)
        ...


الجميل إن:

أي Strategy تشوف نفس كائن CompositeSignal، فتقدر تستغل:

quant.rsi

nlp.sentiment

social.buzz_score

composite.direction/confidence

✅ في نهاية Part 7 يجب أن يكون لديك:

dataclasses مرتبة:

QuantSignals, NLPNewsSignals, SocialSignals, CompositeSignal

دوال:

compute_quant_signals(symbol, df, window=20)

compute_nlp_news_signals(entity) (placeholder)

compute_social_signals(symbol) (placeholder)

build_composite_signal(...)

اللوب يستدعي هذه الدوال، ويسجّل log لكل CompositeSignal

الاستراتيجيات تحصل على CompositeSignal جاهز بدل ما تعيد حساب المؤشرات بنفسها

🤖 Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 7 في الكود

انسخ هذا الـ prompt كما هو:

You are a senior Python quant engineer working on my project SAGE SmartTrade.

CONTEXT:
- The repo already has basic scaffolding with modules: sagetrade/ingestion, sagetrade/signals, sagetrade/strategies, sagetrade/risk, sagetrade/brokers, sagetrade/utils, etc.
- There is a RiskManager and a trading loop in place (Phase 6).
- I now want to implement Phase 7: the Signals Engine (Quant + News/NLP + Social + CompositeSignal).

TASK:

1) In `sagetrade/signals/quant.py`:
   - Define a `QuantSignals` dataclass with fields:
     - symbol: str
     - window: int
     - sma: float
     - ema: float
     - rsi: float
     - atr: float
     - volatility: float
     - regime: str
   - Implement helper functions:
     - `_sma(series: pd.Series, window: int) -> float`
     - `_ema(series: pd.Series, span: int) -> float`
     - `_rsi(series: pd.Series, window: int) -> float`
     - `_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> float`
     - `_volatility(series: pd.Series, window: int) -> float`
     - `_detect_regime(close: pd.Series, window: int) -> str`
   - Implement `compute_quant_signals(symbol: str, df: pd.DataFrame, window: int = 20) -> QuantSignals`.

2) In `sagetrade/signals/nlp_news.py`:
   - Define `NLPNewsSignals` dataclass with:
     - entity: str
     - sentiment: float
     - impact_score: float
     - event_flags: dict[str, bool]
     - language: str
   - Implement a placeholder `compute_nlp_news_signals(entity: str) -> NLPNewsSignals` that:
     - for now returns neutral values (sentiment=0, impact_score=0, some default event_flags).
     - logs a DEBUG message via the existing logging helper.

3) In `sagetrade/signals/social.py`:
   - Define `SocialSignals` dataclass with:
     - symbol: str
     - sentiment: float
     - buzz_score: float
     - volume_score: float
   - Implement a placeholder `compute_social_signals(symbol: str) -> SocialSignals` that:
     - returns neutral values for now.
     - logs a DEBUG message.

4) In `sagetrade/signals/composite.py`:
   - Define `CompositeSignal` dataclass with:
     - symbol: str
     - quant: QuantSignals
     - nlp: Optional[NLPNewsSignals]
     - social: Optional[SocialSignals]
     - score: float
     - direction: str
     - confidence: float
   - Implement `build_composite_signal(...) -> CompositeSignal` that:
     - takes symbol, quant, optional nlp, optional social.
     - computes:
       - a quant_score (e.g. based on normalized RSI).
       - a news_score = nlp.sentiment * nlp.impact_score (if nlp is provided).
       - a social_score = social.sentiment * max(social.buzz_score, 0.1) (if social provided).
     - combines them with weights: quant_weight (default 0.5), news_weight (0.3), social_weight (0.2).
     - clips the final score to [-1, 1].
     - sets direction = "long" if score > threshold, "short" if score < -threshold, else "flat".
     - sets confidence = abs(score).
     - logs an INFO message with event=composite_signal, symbol, direction, score, confidence, regime, rsi.

5) In the main trading loop script (e.g. `scripts/paper_trade_loop.py` or equivalent):
   - Integrate the signals engine:
     - For each symbol:
       - load recent OHLCV bars into a DataFrame.
       - call `compute_quant_signals(symbol, df, window=20)`.
       - call the placeholder `compute_nlp_news_signals(symbol or "market")`.
       - call the placeholder `compute_social_signals(symbol)`.
       - call `build_composite_signal(...)`.
       - pass the resulting `CompositeSignal` into strategies.
     - Log when a composite signal is computed per symbol.

STYLE:
- Use Python 3.11+ typing and dataclasses.
- Use pandas for OHLCV calculations.
- Use the existing logging helpers (`get_logger`) from sagetrade.utils.logging.
- Output code as file blocks with paths, for example:
  # FILE: sagetrade/signals/quant.py
  ...
  # FILE: sagetrade/signals/nlp_news.py
  ...
  # FILE: sagetrade/signals/social.py
  ...
  # FILE: sagetrade/signals/composite.py
  ...
  # FILE: scripts/paper_trade_loop.py
  ...