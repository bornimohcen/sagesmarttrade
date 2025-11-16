Part 5 💾🔥

بما إنك عندك الآن:

Spec (تعريف النظام) ✅

Architecture Blueprint ✅

Scaffolding + Settings ✅

المرحلة 5 هي:

🧱 بناء نظام Logging & Observability محترم

علشان:

تعرف إيش يسوي البوت كل لحظة

تقدر تراجع الصفقات بعدين

تشخّص أي خطأ في ثانيتين بدل ما تغرق في print 😅

رح أقسم لك المرحلة كذا:

الفكرة العامة: ليه نحتاج Logging قوي في بوت تداول

المهام التفصيلية اللي لازم تنعمل

مثال تصميم شكل اللوجات (Standard)

كود مقترح لـ utils/logging.py وتحسينه

كيف نستخدمه في بقية المشروع (broker, risk, strategies, loop)

Prompt جاهز تعطيه لـ AI Agent علشان يبني/يحسن الـ logging في مشروعك

1️⃣ ليه نحتاج Logging قوي في بوت تداول؟

لأن البوت:

يفتح / يغلق صفقات

يتعامل مع فلوس (حتى لو Paper)

يقرأ بيانات من مصادر كثيرة

يعتمد على AI وقرارات شبه معقدة

فإنت تحتاج:

Trace:

متى جاء signal لرمز معين؟

أي strategy قررت فتح الصفقة؟

أي risk rule سمح/منع الصفقة؟

ماذا كان رصيد الحساب وقتها؟

Audit:

بعد أسبوع: “ليش البوت خسر في هذي الصفقة؟”

تفتح الـ log وتشوف كل خطوة.

Debug:

ليه فجأة توقف عن التداول؟

API فشل؟ Rate limit؟ خطأ في parsing؟

2️⃣ تقسيم المرحلة 5 إلى مهام واضحة
🧱 المهمة 5.1 — تصميم Standard لشكل اللوج

نحتاج نتفق على:

الـ format لكل سطر

المعلومات الأساسية اللي لازم تظهر دائمًا

مثال Format (بسيط وواضح):

TIMESTAMP | LEVEL | LOGGER | event=... | key=value key2=value2 ...


مثال Log لسطر trade:

2025-11-14T14:55:47Z | INFO | sagetrade.trading.loop |
event=order_submitted symbol=BTCUSD strategy=news_quick_trade side=sell qty=0.48 price=104.14 account_id=paper-loop


مثال لبلوك من RiskManager:

2025-11-14T14:55:47Z | WARNING | sagetrade.risk.manager |
event=trade_blocked reason=max_trade_risk_pct_exceeded symbol=AAPL risk_pct=0.012 max=0.01

🧱 المهمة 5.2 — مستويات الـ Logging (Levels)

اتفق على استخدام المستويات كالآتي:

DEBUG → تفاصيل تقنية / حسابات داخلية (تشغيلها عند التطوير فقط)

INFO → أحداث طبيعية:

بدأ loop

جاء signal

تم إرسال order

تم إغلاق position

WARNING → شيء مو خطير لكن يستحق انتباه:

API call retry

trade تم منعه بواسطة risk rule

ERROR → خطأ منع جزء من العمل:

فشل في إرسال أوردر للبروكر

CRITICAL → حاجة تهد النظام:

broker down

kill-switch فعل نفسه

🧱 المهمة 5.3 — بناء Logging Setup موحد في utils/logging.py

الأهداف:

إعداد logging مرة واحدة في entrypoint (مثلاً في run_paper_loop.py)

كل Module يحصل على logger باسمه:

logger = logging.getLogger(__name__)


ونوفّر:

Output للـ console

ملف في logs/sagesmarttrade.log

Format موحد

إمكانية إضافة JSON logging لاحقًا

🧱 المهمة 5.4 — إضافة context مهم في كل Log

حاول دائمًا تذكر:

event = اسم الحدث (order_submitted, position_closed, signal_computed, trade_blocked…)

symbol

strategy

account_id

order_id / position_id لو متوفر

تقدر تطبّقه يدويًا (بكتابة event=... symbol=...) أو تبني helper.

🧱 المهمة 5.5 — إضافة Logs في أهم الأماكن

Trading Loop

StrategyManager / strategies

RiskManager

Broker

Telegram bot

AI modules (مثلاً AI شرح صفقة، أو AI حذر من مخاطر)

مثلاً:

عند حساب signal:

logger.info(
    "signal_computed event=signal_computed symbol=%s direction=%s score=%.4f conf=%.3f",
    symbol, composite.direction, composite.score, composite.confidence,
)


عند فتح صفقة:

logger.info(
    "order_submitted event=order_submitted symbol=%s side=%s qty=%.4f price=%.4f strategy=%s account_id=%s",
    order.symbol, order.side, order.qty, order.price, strategy_name, account_id,
)


عند بلوك من Risk:

logger.warning(
    "trade_blocked event=trade_blocked symbol=%s reason=%s risk_pct=%.4f max=%.4f",
    symbol, "max_trade_risk_pct_exceeded", trade_risk_pct, max_trade_risk_pct,
)

3️⃣ كود مقترح لـ sagetrade/utils/logging.py

نفترض إن عندك ملف بسيط قبل، الآن نخليه أقوى شوي:

# FILE: sagetrade/utils/logging.py

from __future__ import annotations

import logging
from logging import Logger
from pathlib import Path
from typing import Optional

from sagetrade.utils.config import get_settings


def setup_logging(level: int = logging.INFO, *, log_to_file: bool = True) -> None:
    """
    Configure root logging for SAGE SmartTrade.

    - Console output with a readable format.
    - Optional file output in logs/sagesmarttrade.log.
    """
    settings = get_settings()
    logs_dir = Path(settings.data.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    handlers: list[logging.Handler] = []

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(console_handler)

    if log_to_file:
        file_handler = logging.FileHandler(logs_dir / "sagesmarttrade.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
    )

    # Optional: reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> Logger:
    """
    Helper to get a logger with the given name.
    If name is None, returns root logger.
    """
    return logging.getLogger(name or "sagetrade")


ثم في أي Module:

# FILE: sagetrade/brokers/paper.py

from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

class PaperBroker(BrokerBase):
    def submit_order(self, order: Order) -> None:
        logger.info(
            "order_submitted event=order_submitted broker=paper symbol=%s side=%s qty=%.4f",
            order.symbol,
            order.side,
            order.qty,
        )
        # باقي التنفيذ...


وفي scripts/run_paper_loop.py:

from sagetrade.utils.logging import setup_logging, get_logger
from sagetrade.utils.config import get_settings

def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    settings = get_settings()
    logger.info(
        "paper_trade_loop_started event=loop_start account_id=%s symbols=%s",
        "paper-loop",
        settings.symbols.default_universe,
    )
    # TODO: باقي الـ loop...

if __name__ == "__main__":
    main()

4️⃣ إضافة Heartbeat / Health Logs

شيء بسيط لكن مهم:

كل دورة من الـ loop يطبع سطر Info مثل:

logger.info(
    "loop_iteration event=loop_iteration account_id=%s equity=%.2f open_trades=%d",
    account_id,
    risk_state.equity,
    risk_state.open_trades,
)


هذا يسهّل عليك:

تعرِف البوت شغّال

تراقب الـ equity في الزمن

5️⃣ ما الذي يجب أن يكون جاهزاً بعد المرحلة 5؟

utils/logging.py جاهز وفيه:

setup_logging()

get_logger()

كل سكريبت entrypoint (مثل run_paper_loop.py) يستدعي setup_logging() قبل أي شيء.

أهم الموديولات تستخدم logger خاص بها:

broker

risk

strategies

trading loop

رسائل اللوج تشمل دائمًا:

event=...

symbol=... (إن وجد)

strategy=... (إن وجد)

account_id=... (إن وجد)

بهذا المستوى، انت تقدر تفتح ملف logs/sagesmarttrade.log وتفهم ماذا حصل أثناء أي جلسة تداول.

🤖 6️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ المرحلة 5

هذا Prompt متكامل، انسخه وعطه لأي AI Agent يشتغل على الريبو:

You are a senior Python backend engineer.

CONTEXT:
- I have a trading project SAGE SmartTrade with modules and a config system already in place.
- I now want to implement a robust logging and observability layer (phase 5).

TASK:
1. Implement `sagetrade/utils/logging.py` with:
   - `setup_logging(level: int = logging.INFO, log_to_file: bool = True)`:
     - Reads logs_dir from `get_settings().data.logs_dir`.
     - Creates logs_dir if missing.
     - Configures console + file handlers.
     - Uses a format like: "%(asctime)s | %(levelname)s | %(name)s | %(message)s" with ISO-like timestamp.
     - Optionally sets external noisy loggers (e.g. urllib3, httpx) to WARNING.
   - `get_logger(name: Optional[str] = None)` that returns `logging.getLogger(name or "sagetrade")`.

2. Update the following modules to use the logger:
   - `scripts/run_paper_loop.py`:
     - Call `setup_logging()` at startup.
     - Log an INFO message "paper_trade_loop_started" with fields: event, account_id, symbols.
   - `sagetrade/brokers/paper.py`:
     - Add logging for order submission and position updates with structured messages including event, symbol, side, qty.
   - `sagetrade/risk/manager.py`:
     - Log when a trade is blocked, with event=trade_blocked, symbol, reason, trade_risk_pct, max_trade_risk_pct.
   - `sagetrade/strategies/base.py` or concrete strategies:
     - Log when a strategy decides to enter or skip a trade, with event=strategy_decision, strategy_name, symbol, decision.

3. Design a simple logging convention:
   - Always include `event=...` as a key in the log message.
   - Where applicable, include: symbol, strategy, account_id, order_id, position_id.

4. Add a heartbeat log in the trading loop:
   - Every iteration, log an INFO with event=loop_iteration, account_id, equity, open_trades.

STYLE:
- Use Python's built-in logging module.
- Keep the implementation clean and idiomatic.
- Show the updated code as file blocks with paths, e.g.:
  # FILE: sagetrade/utils/logging.py
  ...
  # FILE: scripts/run_paper_loop.py
  ...
