Part 8: Strategy Engine (محرك الاستراتيجيات) — المكان اللي يتحول فيه الـ CompositeSignal + RiskState إلى:

“اشتري / بيع / لا تعمل شيء، وبكم؟”

أنا راح أرتّب لك Part 8 كالتالي:

الفكرة العامة: إيش نريد من طبقة الاستراتيجيات؟

تصميم StrategyBase + Config + Registry

استراتيجيتين حقيقيّتين:

news_quick_trade

trend_follow

منطق الدخول / الخروج / position sizing

كيف نربط كل هذا داخل الـ trading loop

Prompt جاهز تعطيه لـ AI Agent ينفّذ Part 8 في مشروعك

🧠 1) ما الذي نريده من Strategy Engine؟

نريد ثلاث أشياء رئيسية:

واجهة موحّدة لجميع الاستراتيجيات

كل استراتيجية كلاس يرث من StrategyBase

لها:

name

symbols (أو شرط على الـ symbol)

should_enter(composite, risk_state)

should_exit(position, composite, risk_state)

position_size(composite, risk_state, price)

نظام تسجيل (registry)

يكتشف كل Strategy تلقائياً من مجلد sagetrade/strategies

يفعّل فقط اللي موجودة في settings.strategies.enabled

فصل واضح بين:

توليد signal (Part 7)

القرار النهائي وكم نخاطر (Strategy Engine + RiskManager من Part 6)

🧩 2) تفكيك Part 8 إلى مهام
🧱 8.1 — تصميم StrategyBase

ملف: sagetrade/strategies/base.py

نريد واجهة عامة:

name: اسم الاستراتيجية

is_enabled_for(symbol: str) -> bool

should_enter(composite, risk_state) -> tuple[bool, str]

should_exit(position, composite, risk_state) -> tuple[bool, str]

position_size(composite, risk_state, price) -> float (كمية الـ qty)

🧱 8.2 — StrategyConfig من settings

نربط الاستراتيجيات بالإعدادات:

strategies:
  enabled:
    - "news_quick_trade"
    - "trend_follow"
  per_symbol:
    BTCUSD:
      - "news_quick_trade"
    AAPL:
      - "trend_follow"


ونبني class صغير:

StrategyConfig أو نستخدم StrategiesSettings اللي عندك
الهدف: الاستراتيجية تعرف هل هي مفعّلة لهذا الرمز أم لا.

🧱 8.3 — Strategy Registry

نحتاج شيء مثل:

StrategyRegistry:
    - register(strategy_class)
    - get_enabled_strategies_for(symbol)


عن طريق decorator أو manual list.

📦 3) تصميم StrategyBase + Registry
📄 base.py (هيكل مقترح)
# FILE: sagetrade/strategies/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Tuple

from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()

class StrategyBase(ABC):
    """Base class for all trading strategies."""
    name: ClassVar[str] = "base"

    def __init__(self) -> None:
        self.settings = _settings

    @abstractmethod
    def is_enabled_for(self, symbol: str) -> bool:
        ...

    @abstractmethod
    def should_enter(self, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        """
        Returns (enter, reason).
        enter: True if we want to open a new position.
        """
        ...

    @abstractmethod
    def should_exit(self, position, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        """
        Returns (exit, reason).
        """
        ...

    @abstractmethod
    def position_size(self, signal: CompositeSignal, risk: RiskState, price: float) -> float:
        """
        Returns qty (units) to trade if entering.
        """
        ...

# -------- Registry --------

class StrategyRegistry:
    _strategies: Dict[str, StrategyBase] = {}

    @classmethod
    def register(cls, strategy_cls: type[StrategyBase]) -> None:
        name = strategy_cls.name
        cls._strategies[name] = strategy_cls()
        logger.info("strategy_registered event=strategy_registered name=%s", name)

    @classmethod
    def all(cls) -> Dict[str, StrategyBase]:
        return cls._strategies

    @classmethod
    def enabled_for_symbol(cls, symbol: str) -> List[StrategyBase]:
        enabled_names = _settings.strategies.enabled
        per_symbol = _settings.strategies.per_symbol or {}
        symbol_specific = per_symbol.get(symbol, enabled_names)

        result: List[StrategyBase] = []
        for name in symbol_specific:
            strat = cls._strategies.get(name)
            if strat is None:
                continue
            if strat.is_enabled_for(symbol):
                result.append(strat)
        return result


الآن أي استراتيجية جديدة:

ترث من StrategyBase

تعيّن name

في نهاية الملف تنادي StrategyRegistry.register(StrategyClass)

🔥 4) استراتيجية 1 — news_quick_trade

فكرتها:

تستغل إشارة خبرية قوية + حركة سعرية سريعة

زمن الاحتفاظ قصير (scalping سريع أو intraday)

منطق مبسّط كبداية:

شرط الدخول:

signal.nlp.impact_score أعلى من threshold (مثلاً 0.3)

abs(signal.nlp.sentiment) أعلى من threshold (مثلاً 0.2)

signal.quant.regime == "high_vol"

confidence > 0.3

الاتجاه:

لو sentiment إيجابي → long

لو سلبي → short

الحجم:

نخاطر بنسبة ثابتة من equity (risk.max_risk_per_trade_pct)

notional = equity * max_risk_per_trade_pct * leverage_factor

qty = notional / price

📄 news_quick_trade.py
# FILE: sagetrade/strategies/news_quick_trade.py

from __future__ import annotations
from typing import Tuple

from sagetrade.strategies.base import StrategyBase, StrategyRegistry
from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

class NewsQuickTradeStrategy(StrategyBase):
    name = "news_quick_trade"

    def is_enabled_for(self, symbol: str) -> bool:
        # يمكنك تضييقها على رموز معينة (مثلاً أسهم فقط)
        # هنا نستخدم إعدادات config.strategies.per_symbol
        per_symbol = self.settings.strategies.per_symbol or {}
        allowed = per_symbol.get(symbol, self.settings.strategies.enabled)
        return self.name in allowed

    def should_enter(self, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        if signal.nlp is None:
            return False, "no_nlp_signal"

        nlp = signal.nlp

        # شروط مبسطة
        if nlp.impact_score < 0.3:
            return False, "low_impact_news"

        if abs(nlp.sentiment) < 0.2:
            return False, "weak_sentiment"

        if signal.quant.regime != "high_vol":
            return False, "not_high_vol_regime"

        if signal.confidence < 0.3:
            return False, "low_composite_confidence"

        # direction يأتي من composite
        if signal.direction == "flat":
            return False, "flat_direction"

        logger.info(
            "[%s] news_quick_trade: ENTER signal=direction:%s score=%.4f sentiment=%.3f impact=%.3f",
            signal.symbol,
            signal.direction,
            signal.score,
            nlp.sentiment,
            nlp.impact_score,
        )
        return True, "ok"

    def should_exit(self, position, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        # مبدئياً: الخروج ممكن يكون:
        # - TP/SL يديره broker أو engine
        # - أو خروج مبكر لو انعكس sentiment / regime
        if signal.nlp and signal.nlp.impact_score < 0.1:
            return True, "news_impact_faded"

        if signal.direction == "flat":
            return True, "composite_flat"

        return False, ""

    def position_size(self, signal: CompositeSignal, risk: RiskState, price: float) -> float:
        equity = risk.equity
        risk_cfg = self.settings.risk
        # نخاطر بمثلاً max_risk_per_trade_pct من equity، لكن لكونها quick trade نخليها أكبر قليلاً
        notional = equity * risk_cfg.max_risk_per_trade_pct * 2.0  # leverage داخلية
        qty = notional / price if price > 0 else 0.0
        return max(qty, 0.0)

# register
StrategyRegistry.register(NewsQuickTradeStrategy)

📈 5) استراتيجية 2 — trend_follow

فكرتها:

تعتمد على اتجاه عام للسعر وليس فقط خبر

تستخدم:

EMA vs SMA

RSI (overbought/oversold)

regime (trending_up / trending_down / high_vol / low_vol)

منطق مبسط:

long إذا:

EMA > SMA

RSI بين 50 و 70

volatility معتدل

short إذا:

EMA < SMA

RSI بين 30 و 50

الخروج لو:

EMA cross عكسي

RSI يدخل منطقة extreme جداً

📄 trend_follow.py
# FILE: sagetrade/strategies/trend_follow.py

from __future__ import annotations
from typing import Tuple

from sagetrade.strategies.base import StrategyBase, StrategyRegistry
from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

class TrendFollowStrategy(StrategyBase):
    name = "trend_follow"

    def is_enabled_for(self, symbol: str) -> bool:
        per_symbol = self.settings.strategies.per_symbol or {}
        allowed = per_symbol.get(symbol, self.settings.strategies.enabled)
        return self.name in allowed

    def should_enter(self, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        q = signal.quant

        # لو كان السوق trending up
        if q.ema > q.sma and 50 < q.rsi < 70:
            logger.info(
                "[%s] trend_follow: ENTER LONG ema=%.2f sma=%.2f rsi=%.2f",
                signal.symbol,
                q.ema,
                q.sma,
                q.rsi,
            )
            # نجبر الاتجاه هنا لو composite أعطى flat
            signal.direction = "long"
            return True, "trend_up"

        # لو trending down
        if q.ema < q.sma and 30 < q.rsi < 50:
            logger.info(
                "[%s] trend_follow: ENTER SHORT ema=%.2f sma=%.2f rsi=%.2f",
                signal.symbol,
                q.ema,
                q.sma,
                q.rsi,
            )
            signal.direction = "short"
            return True, "trend_down"

        return False, "no_trend_setup"

    def should_exit(self, position, signal: CompositeSignal, risk: RiskState) -> Tuple[bool, str]:
        q = signal.quant
        side = position.side  # "long" or "short"

        if side == "long" and (q.ema < q.sma or q.rsi < 45):
            return True, "trend_long_invalidated"

        if side == "short" and (q.ema > q.sma or q.rsi > 55):
            return True, "trend_short_invalidated"

        return False, ""

    def position_size(self, signal: CompositeSignal, risk: RiskState, price: float) -> float:
        equity = risk.equity
        risk_cfg = self.settings.risk
        # trend_follow غالباً position أكبر لكن أقل عدداً
        notional = equity * risk_cfg.max_risk_per_trade_pct * 3.0
        qty = notional / price if price > 0 else 0.0
        return max(qty, 0.0)

StrategyRegistry.register(TrendFollowStrategy)


الأرقام مؤقتة؛ راح تعدّلها لما تبدأ الـ backtesting.

🔗 6) ربط الاستراتيجيات مع الـ trading loop

في سكريبت اللوب (مثل scripts/paper_trade_loop.py):

في بداية السكريبت:

from sagetrade.strategies.base import StrategyRegistry
# مهم: استيراد الملفات حتى يتم التسجيل
import sagetrade.strategies.news_quick_trade  # noqa: F401
import sagetrade.strategies.trend_follow      # noqa: F401


داخل اللوب بعد حساب composite:

strategies = StrategyRegistry.enabled_for_symbol(symbol)
if not strategies:
    logger.debug("[%s] no strategies enabled; skipping.", symbol)
    continue

for strat in strategies:
    enter, reason = strat.should_enter(composite, risk_state)
    if not enter:
        logger.debug(
            "[%s] %s: no entry (%s)",
            symbol,
            strat.name,
            reason,
        )
        continue

    # حدّد الاتجاه من composite / strategy
    direction = composite.direction
    if direction not in ("long", "short"):
        logger.debug("[%s] %s: invalid direction=%s", symbol, strat.name, direction)
        continue

    price = df["close"].iloc[-1]
    qty = strat.position_size(composite, risk_state, price)
    if qty <= 0:
        logger.debug("[%s] %s: position_size=0; skipping", symbol, strat.name)
        continue

    # حوّل direction إلى side "buy"/"sell" حسب نوع السوق (spot)
    side = "buy" if direction == "long" else "sell"
    notional = qty * price

    allowed, risk_reason = risk_manager.can_open_trade(symbol, notional)
    if not allowed:
        logger.info(
            "[%s] %s: BLOCKED by risk manager (%s)",
            symbol,
            strat.name,
            risk_reason,
        )
        continue

    # لو مسموح → إنشاء order وإرسالها لـ broker
    order = Order(symbol=symbol, side=side, qty=qty)
    broker.submit_order(order)


للخروج من الصفقات:

في نفس اللوب أو في جزء مخصص لـ manage_open_positions:

positions = broker.get_open_positions()
for pos in positions:
    symbol = pos.symbol
    df = load_recent_bars(symbol)
    if df is None:
        continue
    composite = process_symbol(symbol, df)
    strategies = StrategyRegistry.enabled_for_symbol(symbol)
    for strat in strategies:
        exit_, reason = strat.should_exit(pos, composite, risk_state)
        if exit_:
            # هنا تبني order بالعكس (مثلاً close أو opposite side)
            ...

✅ بعد Part 8 لازم يكون عندك:

StrategyBase مضبوط + StrategyRegistry

استراتيجيتين على الأقل:

NewsQuickTradeStrategy

TrendFollowStrategy

الـ trading loop:

يحسب CompositeSignal

يمرّها على الاستراتيجيات

كل استراتيجية تقرّر:

ندخل أو لا

حجم الصفقة لو ندخل

قبل الإرسال → يمر على RiskManager (Part 6)

اللوج يبين بوضوح:

استراتيجيات مفعلة لكل رمز

لماذا دخلت صفقة؟

لماذا تم حظرها أو رفضها؟

🤖 Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 8

انسخ هذا الـ prompt كما هو وأرسله لوكيل AI يشتغل على الريبو:

You are a senior Python quant engineer working on my trading project SAGE SmartTrade.

CONTEXT:
- The project already has:
  - A CompositeSignal object (quant + nlp + social).
  - A RiskState and RiskManager with trade gating.
  - A trading loop that can compute CompositeSignals per symbol.

I now want to implement Phase 8: the Strategy Engine (news_quick_trade + trend_follow).

TASK:

1) In `sagetrade/strategies/base.py`:
   - Define an abstract `StrategyBase` class with:
     - ClassVar `name: str`
     - `is_enabled_for(symbol: str) -> bool`
     - `should_enter(signal: CompositeSignal, risk: RiskState) -> tuple[bool, str]`
     - `should_exit(position, signal: CompositeSignal, risk: RiskState) -> tuple[bool, str]`
     - `position_size(signal: CompositeSignal, risk: RiskState, price: float) -> float`
   - Implement a `StrategyRegistry` with:
     - `register(strategy_cls: type[StrategyBase])`
     - `all() -> dict[str, StrategyBase]`
     - `enabled_for_symbol(symbol: str) -> list[StrategyBase]`
   - The registry should consider `settings.strategies.enabled` and `settings.strategies.per_symbol`.

2) In `sagetrade/strategies/news_quick_trade.py`:
   - Implement `NewsQuickTradeStrategy(StrategyBase)` with:
     - `name = "news_quick_trade"`.
     - `is_enabled_for(symbol)` using strategies settings.
     - `should_enter(...)` logic such as:
       - requires `signal.nlp` not None.
       - `impact_score >= 0.3`.
       - `abs(sentiment) >= 0.2`.
       - `signal.quant.regime == "high_vol"`.
       - `signal.confidence >= 0.3`.
       - `signal.direction != "flat"`.
     - `should_exit(...)` example logic:
       - exit when news impact fades or composite direction becomes flat.
     - `position_size(...)`:
       - use `risk.equity * risk_settings.max_risk_per_trade_pct * 2.0` as notional.
       - `qty = notional / price`.
   - Register the strategy via `StrategyRegistry.register(NewsQuickTradeStrategy)`.

3) In `sagetrade/strategies/trend_follow.py`:
   - Implement `TrendFollowStrategy(StrategyBase)` with:
     - `name = "trend_follow"`.
     - `is_enabled_for(symbol)` similar to above.
     - `should_enter(...)` example logic:
       - LONG when `ema > sma` and `50 < rsi < 70`.
       - SHORT when `ema < sma` and `30 < rsi < 50`.
       - set `signal.direction` to "long"/"short" accordingly if needed.
     - `should_exit(...)`:
       - exit when EMA vs SMA or RSI invalidate the trend (e.g. ema cross, rsi dropping below threshold).
     - `position_size(...)`:
       - notional = `risk.equity * risk_settings.max_risk_per_trade_pct * 3.0`.
       - qty = notional / price.
   - Register via `StrategyRegistry.register(TrendFollowStrategy)`.

4) In the main trading loop script (e.g. `scripts/paper_trade_loop.py`):
   - Import the strategies so they register:
     - `import sagetrade.strategies.news_quick_trade`
     - `import sagetrade.strategies.trend_follow`
   - For each symbol:
     - After computing the CompositeSignal, call:
       - `strategies = StrategyRegistry.enabled_for_symbol(symbol)`
     - For each strategy:
       - call `should_enter(signal, risk_state)`.
       - if True:
         - get `price` from latest bar.
         - compute `qty = strategy.position_size(signal, risk_state, price)`.
         - compute `notional = qty * price`.
         - call `risk_manager.can_open_trade(symbol, notional)`.
         - if allowed, build and submit an order via the broker.
   - Log strategy decisions (enter / skip / blocked) at INFO/DEBUG levels with structured messages.

STYLE:
- Use Python 3.11+ typing and dataclasses where appropriate.
- Respect the existing config and logging utilities.
- Output updated/new files as blocks with paths, for example:
  # FILE: sagetrade/strategies/base.py
  ...
  # FILE: sagetrade/strategies/news_quick_trade.py
  ...
  # FILE: sagetrade/strategies/trend_follow.py
  ...
  # FILE: scripts/paper_trade_loop.py
  ...
