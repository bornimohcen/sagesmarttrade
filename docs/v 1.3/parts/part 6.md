Part 6 💣

هذي من أهم المراحل فعليًا، لأنها تربط:

الحساب الحقيقي (Broker)
مع

صورة المخاطر داخل النظام (RiskState)
وتتحكم في:

هل نسمح بصفقة جديدة أو نمنعها؟

كم نُخاطر في كل صفقة؟

متى نوقف التداول بالكامل بسبب خسارة يومية أو Drawdown كبير؟

أنا سأقسم Part 6 كالتالي:

الفكرة العامة: ماذا نريد من RiskState + Broker Summary

تفصيل المهام خطوة خطوة

أمثلة كود توضيحية (state + broker summary + risk manager)

كيف نربط كل هذا مع الـ trading loop

Prompt جاهز لـ AI Agent ينفّذ لك هذه المرحلة في المشروع

🧱 Part 6 — ربط RiskState مع Broker + تفعيل قواعد الدخول (Risk-Aware Trading Loop)
🎯 هدف المرحلة

أن يكون عندك مصدر واحد للحقيقة عن حالة حسابك داخل النظام:

RiskState يعكس:

equity الحالية

realized PnL

open trades

التعرض per symbol

خسارة اليوم الحالية (daily loss)

يتم تحديثه في كل دورة من اللوب من خلال:

broker.get_account_summary()

broker.get_positions()

وأن:

أي صفقة جديدة تمر على RiskManager:

إذا الـ risk مقبول → نسمح بالدخول

إذا غير مقبول → نمنع الصفقة + log واضح

1️⃣ ما الذي نريده من RiskState بالضبط؟

نتخيل RiskState كـ “دفتر مراقبة المخاطر” داخل الـ bot:

يحتوي على مثلاً:

@dataclass
class RiskState:
    equity_start: float            # رصيد بداية اليوم / الجلسة
    equity: float                  # الرصيد الحالي (من broker)
    realized_pnl: float            # الأرباح/الخسائر المغلقة
    open_trades: int               # عدد الصفقات المفتوحة
    open_notional_by_symbol: dict[str, float]  # القيمة المفتوحة لكل رمز
    last_equity_update_ts: float   # آخر تحديث
    session_start_ts: float        # بداية الجلسة / اليوم


ومشتقات:

daily_pnl = equity - equity_start

التأكد من:

daily_pnl >= -max_daily_loss

هذا الـ RiskState هو ما سيمُرّ إلى:

الـ strategies (حتى تتخذ قرار بناءً على الحالة)

الـ RiskManager (ليقرّر block/allow)

2️⃣ ما الذي نريده من BrokerSummary؟

نريد من كل broker (سواء paper أو حقيقي) أن يُعيد لنا summary بشكل موحّد، مثلاً dict:

{
    "balance": 9999.70,
    "equity": 9999.70,
    "realized_pnl": -0.30,
    "open_positions": 12,
    "open_notional": 599.69,
    "per_symbol_notional": {
        "BTCUSD": 200.0,
        "AAPL": 200.0,
        "EURUSD": 200.0,
    },
}


حتى لو طريقة حسابها تختلف بين PaperBroker و AlpacaBroker، المهم:

الواجهة واحدة (interface واحد)

RiskState ما يهتم “كيف” broker حصل على الأرقام، فقط يستهلكها.

3️⃣ تقسيم Part 6 إلى مهام صغيرة
🧱 المهمة 6.1 — توسيع RiskState data model

ملف: sagetrade/risk/state.py

نريد كلاس يحفظ:

Equity البداية

Equity الحالية

Realized PnL

عدد الصفقات المفتوحة

قيمة التعرض لكل رمز

توقيت آخر تحديث

ربما tracking بسيط لـ max drawdown لاحقًا

مثال:

# FILE: sagetrade/risk/state.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict
import time

@dataclass
class RiskState:
    equity_start: float
    equity: float
    realized_pnl: float = 0.0
    open_trades: int = 0
    open_notional_by_symbol: Dict[str, float] = field(default_factory=dict)
    last_equity_update_ts: float = field(default_factory=lambda: time.time())
    session_start_ts: float = field(default_factory=lambda: time.time())

    @property
    def daily_pnl(self) -> float:
        return self.equity - self.equity_start

    @property
    def total_open_notional(self) -> float:
        return sum(self.open_notional_by_symbol.values())

🧱 المهمة 6.2 — توحيد Broker.summary()

ملف: sagetrade/brokers/base.py و sagetrade/brokers/paper.py

في BrokerBase نعرّف:

from abc import ABC, abstractmethod
from typing import Dict, Any

class BrokerBase(ABC):
    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """
        Must return a dict with at least:
        - balance: float
        - equity: float
        - realized_pnl: float
        - open_positions: int
        - open_notional: float
        - per_symbol_notional: dict[str, float]
        """
        ...


في PaperBroker نطبّق:

# FILE: sagetrade/brokers/paper.py

from sagetrade.brokers.base import BrokerBase
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

class PaperBroker(BrokerBase):
    # نفترض أن عندك طريقة لتخزين positions داخلياً
    def get_account_summary(self) -> dict:
        # TODO: غيّر هذا بناءً على منطقك الفعلي
        balance = self._balance
        equity = self._equity
        realized_pnl = self._realized_pnl
        per_symbol_notional = self._compute_per_symbol_notional()
        open_positions = len(self._open_positions)
        open_notional = sum(per_symbol_notional.values())

        summary = {
            "balance": balance,
            "equity": equity,
            "realized_pnl": realized_pnl,
            "open_positions": open_positions,
            "open_notional": open_notional,
            "per_symbol_notional": per_symbol_notional,
        }
        logger.debug("broker_summary event=broker_summary %s", summary)
        return summary


الهدف: عندك الآن نقطة واحدة في النظام تقول لل RiskState:
“هذا هو الوضع الفعلي لحسابك”.

🧱 المهمة 6.3 — كلاس/دالة لتحديث RiskState من broker

ملف: sagetrade/risk/manager.py أو sagetrade/risk/state.py

نضيف helper:

# FILE: sagetrade/risk/manager.py

from sagetrade.risk.state import RiskState
from sagetrade.brokers.base import BrokerBase
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class RiskManager:
    def __init__(self, broker: BrokerBase, risk_state: RiskState):
        self.broker = broker
        self.state = risk_state
        self.cfg = settings.risk

    def refresh_from_broker(self) -> None:
        summary = self.broker.get_account_summary()
        self.state.equity = summary["equity"]
        self.state.realized_pnl = summary["realized_pnl"]
        self.state.open_trades = summary["open_positions"]
        self.state.open_notional_by_symbol = summary["per_symbol_notional"]
        # تحديث timestamp
        self.state.last_equity_update_ts = time.time()

        logger.debug(
            "risk_state_updated event=risk_state_updated equity=%.2f realized_pnl=%.2f open_trades=%d",
            self.state.equity,
            self.state.realized_pnl,
            self.state.open_trades,
        )

    @property
    def daily_pnl(self) -> float:
        return self.state.daily_pnl

🧱 المهمة 6.4 — منطق السماح / المنع لصفقة جديدة (can_open_trade)

هنا الجوهر: قبل ما ترسل Order، تستدعي risk manager:

تحسب “كم نخاطر” في الصفقة (notional أو risk %)

تسأل:

هل هذا أكبر من max_risk_per_trade_pct * equity؟

هل سيجعل exposure على هذا الرمز أكبر من max_symbol_exposure_pct * equity؟

هل daily_pnl أقل من -max_daily_loss_pct * equity_start → يعني hit daily loss؟

نضيف method:

class RiskManager:
    ...

    def can_open_trade(self, symbol: str, notional: float) -> tuple[bool, str]:
        """
        Returns (allowed, reason_if_blocked).
        """
        equity = self.state.equity
        max_trade_risk = self.cfg.max_risk_per_trade_pct * equity
        current_symbol_notional = self.state.open_notional_by_symbol.get(symbol, 0.0)
        max_symbol_exposure = self.cfg.max_symbol_exposure_pct * equity
        max_daily_loss = self.cfg.max_daily_loss_pct * self.state.equity_start

        # 1) Daily loss check
        if self.state.daily_pnl <= -max_daily_loss:
            reason = "max_daily_loss_exceeded"
            logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s daily_pnl=%.2f limit=%.2f",
                symbol,
                reason,
                self.state.daily_pnl,
                -max_daily_loss,
            )
            return False, reason

        # 2) per-trade risk (نفترض notional ~ risk للبساطة في هذه المرحلة)
        if notional > max_trade_risk:
            reason = "max_trade_risk_pct_exceeded"
            logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s notional=%.2f max_trade_risk=%.2f",
                symbol,
                reason,
                notional,
                max_trade_risk,
            )
            return False, reason

        # 3) symbol exposure
        if current_symbol_notional + notional > max_symbol_exposure:
            reason = "max_symbol_exposure_exceeded"
            logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s new_symbol_exposure=%.2f max_symbol_exposure=%.2f",
                symbol,
                reason,
                current_symbol_notional + notional,
                max_symbol_exposure,
            )
            return False, reason

        # 4) max_open_trades
        if self.state.open_trades >= self.cfg.max_open_trades:
            reason = "max_open_trades_exceeded"
            logger.warning(
                "trade_blocked event=trade_blocked symbol=%s reason=%s open_trades=%d max_open_trades=%d",
                symbol,
                reason,
                self.state.open_trades,
                self.cfg.max_open_trades,
            )
            return False, reason

        return True, ""


الآن عندك core risk gate.

🧱 المهمة 6.5 — ربط RiskManager بالـ trading loop قبل إرسال order

ملف: scripts/run_paper_loop.py أو scripts/paper_trade_loop.py في مشروعك.

الفكرة الأساسية في الـ loop:

في بداية كل دورة:

risk_manager.refresh_from_broker()

عندما تستخرج signal و strategy تريد فتح صفقة:

تحسب الحجم (position sizing → سيأتي تفصيليًا في جزء لاحق)

تحسب قيمة الصفقه بالدولار notional = qty * price

تستدعي:

allowed, reason = risk_manager.can_open_trade(symbol, notional)
if not allowed:
    logger.info(
        "[%s] %s: BLOCKED by risk manager (%s)",
        symbol,
        strategy_name,
        reason,
    )
    continue   # لا ترسل الأوردر


إذا مسموح:

تبني order

ترسله via broker

risk state سيتم تحديثه في الدورة القادمة.

Pseudo-code:

def run_loop():
    setup_logging()
    settings = get_settings()
    broker = PaperBroker(...)
    # تهيئة RiskState ببداية اليوم/الجلسة
    equity_start = broker.get_account_summary()["equity"]
    risk_state = RiskState(equity_start=equity_start, equity=equity_start)
    risk_manager = RiskManager(broker, risk_state)

    while True:
        # 1) حدّث RiskState من broker
        risk_manager.refresh_from_broker()

        for symbol in settings.symbols.default_universe:
            # 2) احضر الأسعار، احسب signals (سيأتي في جزء لاحق)
            composite = compute_composite_signal(symbol)

            # 3) استراتيجية مثلاً news_quick_trade تقرر الدخول
            qty, side = strategy_decide(composite, risk_state)
            if qty is None:
                continue

            price = get_last_price(symbol)
            notional = qty * price

            allowed, reason = risk_manager.can_open_trade(symbol, notional)
            if not allowed:
                logger.info(
                    "[%s] %s: BLOCKED by risk manager (%s)",
                    symbol,
                    "news_quick_trade",
                    reason,
                )
                continue

            # 4) إرسال الأوردر
            order = Order(symbol=symbol, side=side, qty=qty)
            broker.submit_order(order)

        logger.info(
            "loop_iteration event=loop_iteration equity=%.2f open_trades=%d daily_pnl=%.2f",
            risk_state.equity,
            risk_state.open_trades,
            risk_state.daily_pnl,
        )
        time.sleep(SLEEP_SEC)

4️⃣ ما الذي يجب أن يكون جاهزًا بعد Part 6؟

RiskState يتحدّث من broker في كل دورة.

RiskManager يمتلك logic واضح:

max_risk_per_trade_pct

max_symbol_exposure_pct

max_daily_loss_pct

max_open_trades

الـ trading loop لا يفتح صفقة جديدة إلا بعد:

قراءة risk state

استدعاء can_open_trade(symbol, notional)

الـ logs تظهر بوضوح:

لماذا تم فتح صفقة

لماذا تم حظر صفقة بسبب المخاطر

هذا سيمنع ما كان يحصل عندك سابقًا:
فتح عشرات الصفقات لنفس الرمز كل 5 ثواني بدون سقف 😅

🤖 5️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 6 في مشروعك

انسخ هذا الـ Prompt وقدّمه لوكيل AI (أو حتى لي في جلسة جديدة):

You are a senior Python engineer working on my trading project SAGE SmartTrade.

CONTEXT:
- The project already has:
  - basic scaffolding for modules: risk, brokers, strategies, utils, scripts
  - a configuration system with risk settings (max_risk_per_trade_pct, max_daily_loss_pct, max_symbol_exposure_pct, max_open_trades)
  - basic logging.

I now want to implement Phase 6:
**Connect RiskState with Broker summary and enforce risk-aware trade gating.**

TASK:

1. In `sagetrade/risk/state.py`:
   - Define a `RiskState` dataclass with fields:
     - equity_start: float
     - equity: float
     - realized_pnl: float
     - open_trades: int
     - open_notional_by_symbol: dict[str, float]
     - last_equity_update_ts: float
     - session_start_ts: float
   - Add properties:
     - `daily_pnl` = equity - equity_start
     - `total_open_notional` = sum of per-symbol notional.

2. In `sagetrade/brokers/base.py`:
   - Ensure `BrokerBase` defines an abstract `get_account_summary()` method returning a dict with keys:
     - balance, equity, realized_pnl, open_positions, open_notional, per_symbol_notional.

3. In `sagetrade/brokers/paper.py`:
   - Implement `get_account_summary()` to compute the above fields from the internal positions and cash.
   - Log the summary at DEBUG level using the existing logging helper.

4. In `sagetrade/risk/manager.py`:
   - Implement a `RiskManager` class that:
     - Accepts a `BrokerBase` and a `RiskState`.
     - Has a `refresh_from_broker()` method that:
       - calls `broker.get_account_summary()`
       - updates `RiskState.equity`, `realized_pnl`, `open_trades`, `open_notional_by_symbol`, `last_equity_update_ts`.
     - Has a `can_open_trade(symbol: str, notional: float) -> tuple[bool, str]` method that:
       - reads risk limits from config (max_risk_per_trade_pct, max_daily_loss_pct, max_symbol_exposure_pct, max_open_trades)
       - checks:
         - daily loss not exceeded
         - notional <= max_trade_risk = max_risk_per_trade_pct * equity
         - per-symbol exposure <= max_symbol_exposure_pct * equity
         - open_trades < max_open_trades
       - returns (False, "reason") if any rule is violated, logging a WARNING with event=trade_blocked.

5. In the main trading loop script (e.g. `scripts/run_paper_loop.py` or equivalent):
   - Initialize a broker and get initial equity.
   - Initialize `RiskState(equity_start=initial_equity, equity=initial_equity, ...)`.
   - Initialize `RiskManager(broker, risk_state)`.
   - On each loop iteration:
     - Call `risk_manager.refresh_from_broker()`.
     - For each symbol and strategy, before submitting an order:
       - compute notional = qty * price
       - call `can_open_trade(symbol, notional)`
       - if not allowed, skip order and log the reason.
   - Log a heartbeat INFO message each iteration with:
     - event=loop_iteration, equity, open_trades, daily_pnl.

STYLE:
- Use Python 3.11+ type hints and dataclasses.
- Integrate with existing `get_settings()` and logging utilities.
- Output code as file blocks with paths, for example:
  # FILE: sagetrade/risk/state.py
  ...
  # FILE: sagetrade/risk/manager.py
  ...
  # FILE: sagetrade/brokers/base.py
  ...
  # FILE: sagetrade/brokers/paper.py
  ...
  # FILE: scripts/run_paper_loop.py
  ...
