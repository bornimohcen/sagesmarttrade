Part 14 = Monitoring & Dashboard & Alerts
الهدف:

تشوف أداء البوت لايف وبعدياً (historical)

بدون ما تفتح لوجات طويلة مملة

ومع تنبيهات لما شيء خطير يحصل (drawdown، عدد صفقات غير طبيعي، إلخ)

رح أقسم Part 14 كذا:

الهدف بالضبط من Part 14

ما هي الـ Metrics اللي نريد مراقبتها

Layer لتجميع الـ Metrics (MetricsCollector)

تخزين البيانات: ملفات / SQLite / Parquet

Dashboard (مثلاً بـ Streamlit) + سكربت تشغيل

Alerts عبر Telegram (مكمل للي عندك)

Prompt جاهز تعطيه لـ AI Agent يطبّق Part 14 في الريبو

1️⃣ الهدف من Part 14

نبغى:

لوحة متابعة (Dashboard) تبين:

Equity Curve

Daily PnL

Open positions

Exposure per symbol / strategy / asset class

عدد الصفقات، win rate تقريبية، إلخ

Monitoring Layer:

كل مرة اللوب يلف (في الـ live/paper trading loop و في backtest)

يكتب snapshot من:

حساب البوركر

RiskState

PortfolioExposure

Counters للصفقات

Alerts:

لو:

daily_loss < -X%

max_drawdown تعدّى حد معيّن

عدد صفقات مفتوحة لا منطقي
→ يرسل تحذير على تيليغرام 🛑

2️⃣ ما هي الـ Metrics اللي نريدها؟

نقسمها إلى 3 أنواع:

📌 2.1 — Account & Risk

لكل timestamp:

balance

equity

realized_pnl

unrealized_pnl (لو متوفر)

daily_pnl

open_trades

total_open_notional

max_drawdown (لو تحسبه تدريجياً)

📌 2.2 — Portfolio Exposure

لكل timestamp:

by_symbol_notional:

BTCUSD: 500$

AAPL: 300$

EURUSD: 200$

by_strategy_notional:

news_quick_trade: 600$

trend_follow: 400$

by_asset_class_notional:

crypto: 500$

equity: 300$

forex: 200$

📌 2.3 — Trade Counters

total_trades

trades_today

win_trades

loss_trades

avg_trade_pnl (تقريبي)

last_trade_pnl

last_trade_symbol, strategy, side

3️⃣ Layer لتجميع الـ Metrics (MetricsCollector)
🧱 14.1 — MetricsSnapshot model

ملف جديد:
/sagetrade/monitoring/models.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any

@dataclass
class MetricsSnapshot:
    ts: datetime

    # Account / risk
    equity: float
    balance: float
    realized_pnl: float
    daily_pnl: float
    open_trades: int
    total_open_notional: float

    # Portfolio exposure
    by_symbol_notional: Dict[str, float]
    by_strategy_notional: Dict[str, float]
    by_asset_class_notional: Dict[str, float]

    # Trade stats (simple approx)
    total_trades: int
    win_trades: int
    loss_trades: int
    last_trade_pnl: float | None = None
    last_trade_symbol: str | None = None
    last_trade_strategy: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

🧱 14.2 — MetricsCollector واجهة بسيطة

ملف:
/sagetrade/monitoring/collector.py

فكرة:

class مسؤول أنه:

يأخذ Snapshot

يخزنها في:

ملف JSONL

أو SQLite

يستخدمه كل من:

live loop

paper_trade_loop

backtest runner (اختياري)

# FILE: sagetrade/monitoring/collector.py

from __future__ import annotations
from pathlib import Path
import json
from typing import Optional

from sagetrade.monitoring.models import MetricsSnapshot
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

class MetricsCollector:
    def __init__(self, out_dir: str = "data/metrics", file_prefix: str = "metrics") -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.out_dir / f"{file_prefix}.jsonl"

    def record(self, snapshot: MetricsSnapshot) -> None:
        try:
            with self.file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.error("metrics_record_error event=metrics_record_error error=%s", exc)

🧱 14.3 — دالة helper تبني Snapshot من RiskState + Broker + PortfolioExposure

ملف:
/sagetrade/monitoring/helpers.py

from __future__ import annotations
from datetime import datetime

from sagetrade.monitoring.models import MetricsSnapshot
from sagetrade.risk.state import RiskState
from sagetrade.portfolio.state import PortfolioExposure
from sagetrade.trades.stats import TradeStats  # لو ما عندك، نضيفه بسيط

def make_snapshot(
    ts: datetime,
    risk: RiskState,
    exposure: PortfolioExposure,
    trade_stats: TradeStats,
) -> MetricsSnapshot:
    return MetricsSnapshot(
        ts=ts,
        equity=risk.equity,
        balance=risk.equity,  # أو من broker.get_account_summary()["balance"]
        realized_pnl=risk.realized_pnl,
        daily_pnl=risk.daily_pnl,
        open_trades=risk.open_trades,
        total_open_notional=exposure.total_notional,
        by_symbol_notional=exposure.by_symbol,
        by_strategy_notional=exposure.by_strategy,
        by_asset_class_notional=exposure.by_asset_class,
        total_trades=trade_stats.total_trades,
        win_trades=trade_stats.win_trades,
        loss_trades=trade_stats.loss_trades,
        last_trade_pnl=trade_stats.last_trade_pnl,
        last_trade_symbol=trade_stats.last_trade_symbol,
        last_trade_strategy=trade_stats.last_trade_strategy,
    )


لو ما عندك TradeStats، نعمل dataclass بسيط في ملف sagetrade/trades/stats.py.

4️⃣ تخزين البيانات: ملفات / SQLite / Parquet

المرحلة الأولى (أسهل): JSONL

كما في MetricsCollector

كل سطر Snapshot = JSON

Dashboard يقرأ الملف و يحوله DataFrame

لاحقاً:

تقدر تضيف Writer ثاني:

SQLiteMetricsWriter

أو ParquetMetricsWriter
لكن حالياً JSONL يكفي ويشتغل مع pandas بسهولة.

5️⃣ Dashboard (بـ Streamlit مثلاً)

نضيف Dashboard بسيط:

ملف: dashboards/trading_dashboard.py (خارج sagetrade، في root المشروع)

🧱 14.4 — Streamlit dashboard (هيكل)
# FILE: dashboards/trading_dashboard.py

import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

METRICS_PATH = Path("data/metrics/metrics.jsonl")

def load_metrics() -> pd.DataFrame:
    if not METRICS_PATH.exists():
        return pd.DataFrame()
    rows = []
    with METRICS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts")
    return df

def main():
    st.set_page_config(page_title="SAGE SmartTrade Dashboard", layout="wide")
    st.title("📊 SAGE SmartTrade — Monitoring Dashboard")

    df = load_metrics()
    if df.empty:
        st.warning("No metrics data found yet. Run the trading loop to generate metrics.")
        return

    # Sidebar filters
    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start date", df["ts"].min().date())
    end_date = st.sidebar.date_input("End date", df["ts"].max().date())

    mask = (df["ts"].dt.date >= start_date) & (df["ts"].dt.date <= end_date)
    df = df[mask]

    st.subheader("Equity & Daily PnL")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart(df.set_index("ts")["equity"])
    with col2:
        st.bar_chart(df.set_index("ts")["daily_pnl"])

    st.subheader("Exposure — by Symbol")
    # by_symbol_notional هي dict، نعمل لها expand
    exp_rows = []
    for _, row in df.iterrows():
        ts = row["ts"]
        by_symbol = row.get("by_symbol_notional") or {}
        for sym, val in by_symbol.items():
            exp_rows.append({"ts": ts, "symbol": sym, "notional": val})
    if exp_rows:
        exp_df = pd.DataFrame(exp_rows)
        # اختيار رمز من sidebar
        symbols = sorted(exp_df["symbol"].unique())
        selected_symbol = st.sidebar.selectbox("Symbol", symbols, index=0)
        exp_sym = exp_df[exp_df["symbol"] == selected_symbol]
        st.line_chart(exp_sym.set_index("ts")["notional"])

    st.subheader("Trade Stats (Overview)")
    last_row = df.iloc[-1]
    col3, col4, col5, col6 = st.columns(4)
    col3.metric("Equity", f"{last_row['equity']:.2f}")
    col4.metric("Total trades", int(last_row["total_trades"]))
    col5.metric("Win trades", int(last_row["win_trades"]))
    col6.metric("Loss trades", int(last_row["loss_trades"]))

    st.subheader("Raw metrics data")
    st.dataframe(df.tail(100))

if __name__ == "__main__":
    main()

🧱 14.5 — سكربت تشغيل

ببساطة في README أو أمر:

streamlit run dashboards/trading_dashboard.py


أو سكربت صغير:

# FILE: scripts/run_dashboard.py
#!/usr/bin/env python3
import os
import subprocess

def main():
    subprocess.run(["streamlit", "run", "dashboards/trading_dashboard.py"])

if __name__ == "__main__":
    main()

6️⃣ Alerts عبر Telegram
🧱 14.6 — Alert Rules

ملف: sagetrade/monitoring/alerts.py

نعرّف قواعد بسيطة:

from __future__ import annotations
from sagetrade.monitoring.models import MetricsSnapshot

def check_alerts(snapshot: MetricsSnapshot, config) -> list[str]:
    msgs: list[str] = []

    # 1) daily loss
    if snapshot.daily_pnl < -config.max_daily_loss_alert:
        msgs.append(f"⚠️ خسارة يومية كبيرة: {snapshot.daily_pnl:.2f}")

    # 2) too many open trades
    if snapshot.open_trades > config.max_open_trades_alert:
        msgs.append(f"⚠️ عدد الصفقات المفتوحة عالي: {snapshot.open_trades}")

    # 3) leverage/exposure ممكن تضيف لاحقاً

    return msgs


في settings:

monitoring:
  alerts:
    max_daily_loss_alert: 200.0   # لو خسر اليوم أكثر من 200$
    max_open_trades_alert: 20

🧱 14.7 — ربطها مع Telegram

في الـ trading loop (أو في مكان مركزي):

بعد ما تبني snapshot وتمرره إلى MetricsCollector:

snapshot = make_snapshot(now, risk_state, portfolio_exposure, trade_stats)
metrics_collector.record(snapshot)

alerts = check_alerts(snapshot, settings.monitoring.alerts)
for msg in alerts:
    telegram_notifier.send_message(msg)


telegram_notifier ممكن يكون wrapper بسيط حول bot:

class TelegramNotifier:
    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id

    async def send_message(self, text: str):
        await self.bot.send_message(chat_id=self.chat_id, text=text)


كذا أي Rule جديدة تضيفها في alerts.py، تلقائياً تبين في التليغرام وقت التنفيذ.

7️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 14

انسخ هذا النص كما هو للـ Agent اللي يعدّل الريبو:

You are a senior backend and quant engineer working on my project SAGE SmartTrade.

CONTEXT:
- The project has:
  - Live/paper trading loop.
  - RiskManager, Portfolio-aware state (Phase 13).
  - Backtest runner and strategy optimization (Phases 11–12).
  - Telegram bot already integrated for notifications.

GOAL (Phase 14):
- Implement a monitoring layer that periodically records trading metrics.
- Provide a simple dashboard (e.g. using Streamlit) to visualize equity, PnL, and exposures.
- Add basic Telegram alerts based on metrics (e.g. large daily loss, too many open trades).

TASKS:

1) Metrics models and collector.

   - File: `sagetrade/monitoring/models.py`
     - Define a `MetricsSnapshot` dataclass with fields:
       - ts: datetime
       - equity: float
       - balance: float
       - realized_pnl: float
       - daily_pnl: float
       - open_trades: int
       - total_open_notional: float
       - by_symbol_notional: dict[str, float]
       - by_strategy_notional: dict[str, float]
       - by_asset_class_notional: dict[str, float]
       - total_trades: int
       - win_trades: int
       - loss_trades: int
       - last_trade_pnl: float | None
       - last_trade_symbol: str | None
       - last_trade_strategy: str | None
     - Add a `to_dict()` method (using `asdict`).

   - File: `sagetrade/monitoring/collector.py`
     - Implement `MetricsCollector` that:
       - On init, takes `out_dir` and `file_prefix` (default: "data/metrics", "metrics").
       - Appends snapshots as JSONL lines to `<out_dir>/<file_prefix>.jsonl` via a `record(snapshot)` method.

   - File: `sagetrade/monitoring/helpers.py`
     - Implement `make_snapshot(ts, risk: RiskState, exposure: PortfolioExposure, trade_stats: TradeStats) -> MetricsSnapshot`.
     - `PortfolioExposure` comes from Phase 13.
     - `TradeStats` can be a simple dataclass in `sagetrade/trades/stats.py` with:
       - total_trades, win_trades, loss_trades, last_trade_pnl, last_trade_symbol, last_trade_strategy.

2) Integration into the trading loop.

   - In the live/paper trading loop (e.g. `scripts/paper_trade_loop.py` or the core engine):
     - After each iteration:
       - Build a `PortfolioExposure` using current broker positions (Phase 13).
       - Maintain/update a `TradeStats` object whenever a trade is closed.
       - Call `make_snapshot(...)` and `metrics_collector.record(snapshot)`.

3) Basic alerts.

   - Extend `config/settings.yaml` with a `monitoring.alerts` section:

     ```yaml
     monitoring:
       alerts:
         max_daily_loss_alert: 200.0
         max_open_trades_alert: 20
     ```

   - File: `sagetrade/monitoring/alerts.py`
     - Implement `check_alerts(snapshot: MetricsSnapshot, alerts_cfg) -> list[str]` that:
       - Adds a message if `daily_pnl < -max_daily_loss_alert`.
       - Adds a message if `open_trades > max_open_trades_alert`.
     - Later it can be extended with leverage/exposure alerts.

   - In the trading loop:
     - After recording a snapshot, call `check_alerts(...)`.
     - For each non-empty alert message, send it via the Telegram bot (reuse existing bot/notifier).

4) Streamlit dashboard.

   - Create directory `dashboards/`.
   - File: `dashboards/trading_dashboard.py`
     - Uses Streamlit to:
       - Load JSONL metrics from `data/metrics/metrics.jsonl` into a pandas DataFrame.
       - Sort by timestamp (`ts`).
       - Provide sidebar date filters for start/end.
       - Show:
         - Line chart of `equity` vs time.
         - Bar chart of `daily_pnl` vs time.
       - Expand `by_symbol_notional` into a long format and:
         - Show a line chart of notional exposure over time for a selected symbol (selectbox in sidebar).
       - Show key stats in `st.metric` cards:
         - equity, total_trades, win_trades, loss_trades (from last row).
       - Show a dataframe of the last ~100 rows for debugging.

   - Optionally, create `scripts/run_dashboard.py` that simply calls:

     ```python
     subprocess.run(["streamlit", "run", "dashboards/trading_dashboard.py"])
     ```

     so I can run `python scripts/run_dashboard.py`.

5) Clean integration & style.

   - Reuse `get_logger` for any logging in the monitoring modules.
   - Make sure metrics recording is robust:
     - Wrap file write in try/except and log errors.
   - Keep the monitoring modules independent (they should not depend on Telegram directly; Telegram integration happens in the loop).

OUTPUT:
- Provide new or updated files as code blocks, e.g.:

  # FILE: sagetrade/monitoring/models.py
  ...
  # FILE: sagetrade/monitoring/collector.py
  ...
  # FILE: sagetrade/monitoring/helpers.py
  ...
  # FILE: sagetrade/trades/stats.py
  ...
  # FILE: sagetrade/monitoring/alerts.py
  ...
  # FILE: dashboards/trading_dashboard.py
  ...
  # FILE: scripts/run_dashboard.py
  ...
  # FILE: scripts/paper_trade_loop.py
  ...

