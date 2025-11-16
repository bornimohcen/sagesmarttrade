Part 11 = Backtesting & Performance Reports
هنا نبدأ نجاوب على السؤال المهم:

“هل البوت فعلاً يربح ولا بس يسوّي حركات؟”

رح أرتّب Part 11 كذا:

الهدف من الـ Backtesting في SAGE_SMART_TRADE

تقسيم Part 11 لمهام واضحة

تصميم BacktestBroker + TradeLog

تصميم BacktestRunner (loop يشبه الـ live loop لكن على التاريخ)

تصميم Metrics & Reports (CSV + summary + per-strategy)

سكربت CLI: scripts/backtest.py

Prompt جاهز تعطيه لـ AI Agent يطبق Part 11 على الريبو

1️⃣ الهدف من الـ Backtesting

نريد:

تشغيل نفس الاستراتيجيات و نفس الـ RiskManager و نفس الـ Signal Engine
لكن بدلاً من الأسعار الحيّة → نستخدم تاريخ OHLCV من ملفات:

data/market/YYYY-MM-DD/SYMBOL.jsonl
أو DataFrame من أي مصدر.

تسجيل كل صفقة في TradeLog مرتب:

entry_time, exit_time

symbol, strategy

side, qty, entry_price, exit_price

PnL, PnL% على الحساب، drawdown… إلخ

في النهاية:

Report:

إجمالي PnL

عدد الصفقات

win rate

max drawdown

Sharpe تقريبي

نتائج per-strategy و per-symbol

2️⃣ تقسيم Part 11 لمهام
🧱 11.1 — Data Loader للتاريخ (Historical OHLCV)

ملف جديد مثل:
/sagetrade/backtest/data_loader.py

دالة:

load_ohlcv_history(symbol: str, start: date, end: date) -> pd.DataFrame

ممكن تعيد DataFrame بعمود timestamp + OHLCV لكل الفترات المطلوبة.

🧱 11.2 — BacktestBroker

ملف:
sagetrade/brokers/backtest.py

يشبه PaperBroker لكن:

يشتغل على timeline تاريخية

يحسب fills بسعر الشمعة (close أو mid)

يحسّب unrealized/realized PnL مع الوقت

يدعم:

submit_order(order)

get_open_positions()

get_account_summary()

🧱 11.3 — TradeLog & Execution Log

ملف:
sagetrade/backtest/trade_log.py

Data model:

BacktestTradeRecord

BacktestBarSnapshot (اختياري)

دوال:

log_fill(order, position)

log_close(position, pnl, ts)

to_csv(path)

🧱 11.4 — BacktestRunner (قلب الباكتيست)

ملف:
sagetrade/backtest/runner.py

يأخذ:

symbols

تاريخ start/end

قائمة strategies

إعدادات المخاطر

يمشي bar-by-bar (أو candle-by-candle):

يحدّث السعر في broker

يحسب CompositeSignal

ينادي الاستراتيجيات

يمر عبر RiskManager

يرسل orders للبروكر

يسجل اللوجات

🧱 11.5 — Metrics & Reports

ملف:
sagetrade/backtest/report.py

دوال:

compute_equity_curve(trades) -> pd.Series

compute_metrics(trades) -> dict

total_return

max_drawdown

win_rate

avg_win, avg_loss

sharpe (تقريبي)

summarize_by_strategy(trades) -> DataFrame

summarize_by_symbol(trades) -> DataFrame

🧱 11.6 — سكربت CLI: scripts/backtest.py

Args:

--symbols BTCUSD,AAPL,EURUSD

--strategies news_quick_trade,trend_follow

--start 2025-01-01

--end 2025-03-31

--out reports/backtest_...

يقرا البيانات، يشغّل runner، يكتب:

trades.csv

summary.json أو summary.txt

3️⃣ تصميم BacktestBroker + TradeLog
📄 Data Model بسيط للـ trade record
# FILE: sagetrade/backtest/trade_log.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import csv

@dataclass
class BacktestTradeRecord:
    trade_id: str
    symbol: str
    strategy_name: str
    side: str            # "long" or "short"
    qty: float
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    realized_pnl: float
    max_favorable_excursion: float  # optional (MFE)
    max_adverse_excursion: float    # optional (MAE)

class TradeLog:
    def __init__(self) -> None:
        self.trades: List[BacktestTradeRecord] = []

    def add_trade(self, record: BacktestTradeRecord) -> None:
        self.trades.append(record)

    def to_csv(self, path: str) -> None:
        if not self.trades:
            return
        fieldnames = list(asdict(self.trades[0]).keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in self.trades:
                writer.writerow(asdict(t))

📄 BacktestBroker skeleton
# FILE: sagetrade/brokers/backtest.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

from sagetrade.brokers.base import BrokerBase
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class BacktestPosition:
    id: str
    symbol: str
    side: str           # "long" or "short"
    qty: float
    entry_price: float
    opened_at: datetime
    closed_at: datetime | None = None
    realized_pnl: float = 0.0
    strategy_name: str | None = None
    meta: dict = field(default_factory=dict)

class BacktestBroker(BrokerBase):
    """
    بسيط: لا يوجد slippage حقيقي في البداية.
    يملأ الأوردر بسعر close للشمعة الحالية.
    """
    def __init__(self, initial_equity: float) -> None:
        self._equity = initial_equity
        self._cash = initial_equity
        self._positions: Dict[str, BacktestPosition] = {}   # symbol -> position (واحدة لكل رمز كبداية)
        self._next_pos_id = 1
        self._now: datetime | None = None

    def set_time(self, ts: datetime) -> None:
        self._now = ts

    def submit_order(self, order) -> None:
        # نتعامل مع order بسيط: side ("buy"/"sell"), qty, symbol, price نمرره من الخارج
        price = order.price
        symbol = order.symbol
        side = order.side  # "buy"/"sell"
        if side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {side}")

        # تحويل side spot إلى "long"/"short"
        pos_side = "long" if side == "buy" else "short"
        notional = price * order.qty

        # هنا نعمل fill فوري
        pos_id = f"bt-pos-{self._next_pos_id}"
        self._next_pos_id += 1

        pos = BacktestPosition(
            id=pos_id,
            symbol=symbol,
            side=pos_side,
            qty=order.qty,
            entry_price=price,
            opened_at=self._now or datetime.utcnow(),
            strategy_name=getattr(order, "strategy_name", None),
        )
        self._positions[pos.symbol + "-" + pos_side + "-" + pos_id] = pos

        # تحديث الكاش التقريبي (للـ long فقط كبداية)
        # يمكنك أن تجعلها أدق لاحقاً
        if pos_side == "long":
            self._cash -= notional
        else:
            # short: نستلم قيمة البيع الآن لكن نتحمل الالتزام
            self._cash += notional

        logger.debug(
            "backtest_order_filled event=backtest_order_filled symbol=%s side=%s qty=%.4f price=%.4f",
            symbol,
            side,
            order.qty,
            price,
        )

    def close_position(self, pos: BacktestPosition, price: float) -> float:
        """
        يغلق position بسعر price، يرجع realized_pnl.
        """
        if pos.closed_at is not None:
            return pos.realized_pnl

        if pos.side == "long":
            pnl = (price - pos.entry_price) * pos.qty
        else:
            pnl = (pos.entry_price - price) * pos.qty

        pos.realized_pnl = pnl
        pos.closed_at = self._now or datetime.utcnow()
        self._equity += pnl
        self._cash += price * pos.qty if pos.side == "long" else -price * pos.qty

        logger.debug(
            "backtest_position_closed event=backtest_position_closed symbol=%s side=%s qty=%.4f entry=%.4f exit=%.4f pnl=%.4f",
            pos.symbol,
            pos.side,
            pos.qty,
            pos.entry_price,
            price,
            pnl,
        )
        return pnl

    def get_open_positions(self) -> List[BacktestPosition]:
        return [p for p in self._positions.values() if p.closed_at is None]

    def get_account_summary(self) -> dict:
        # unrealized PnL يمكن حسابه لاحقاً إن أردت، حالياً نعتبر equity ~ cash
        open_positions = self.get_open_positions()
        summary = {
            "balance": self._cash,
            "equity": self._equity,
            "realized_pnl": self._equity - self._cash,  # تبسيط
            "open_positions": len(open_positions),
            "open_notional": 0.0,
            "per_symbol_notional": {},
        }
        return summary


هذا skeleton فقط؛ الـ Agent يقدر يضبط التفاصيل حسب تصميمك الحالي للـ Order/Position.

4️⃣ BacktestRunner (يشبه live loop لكن على التاريخ)
الفكرة:

بدل while True وحاضر/مستقبل…

نسوي loop على كل بار تاريخي:

تحديث الوقت في broker: broker.set_time(ts)

تحديث price (نمرره عبر df)

بناء DataFrame حتى البار الحالي → compute_quant_signals(...)

بناء CompositeSignal

إستدعاء الاستراتيجيات → قرارات دخول/خروج

RiskManager (نفسه)

Skeleton:
# FILE: sagetrade/backtest/runner.py

from __future__ import annotations
from datetime import datetime, date
from typing import List

import pandas as pd

from sagetrade.brokers.backtest import BacktestBroker, BacktestPosition
from sagetrade.risk.state import RiskState
from sagetrade.risk.manager import RiskManager
from sagetrade.signals.quant import compute_quant_signals
from sagetrade.signals.nlp_news import compute_nlp_news_signals
from sagetrade.signals.social import compute_social_signals
from sagetrade.signals.composite import build_composite_signal
from sagetrade.strategies.base import StrategyRegistry
from sagetrade.backtest.trade_log import TradeLog, BacktestTradeRecord
from sagetrade.utils.logging import get_logger

logger = get_logger(__name__)

def run_backtest(
    symbols: List[str],
    start: date,
    end: date,
    initial_equity: float,
    load_history_fn,
) -> TradeLog:
    """
    load_history_fn(symbol, start, end) -> pd.DataFrame with columns: timestamp, open, high, low, close, volume
    """
    broker = BacktestBroker(initial_equity=initial_equity)
    # تهيئة RiskState Equity البداية
    risk_state = RiskState(equity_start=initial_equity, equity=initial_equity)
    risk_manager = RiskManager(broker, risk_state)
    trade_log = TradeLog()

    # تحميل بيانات كل symbol
    history: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = load_history_fn(sym, start, end)
        if df is None or df.empty:
            logger.warning("No history for symbol=%s; skipping.", sym)
            continue
        # نتأكد timestamp كـ datetime index
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
        history[sym] = df

    # loop على الزمن (نفترض نفس الـ index لكل symbols أو ناخذ union مع forward-fill)
    # لتحسين: نبني timeline موحدة
    for sym, df in history.items():
        logger.info("Backtesting symbol=%s bars=%d", sym, len(df))

        strategies = StrategyRegistry.enabled_for_symbol(sym)
        if not strategies:
            logger.info("No strategies enabled for symbol=%s; skipping.", sym)
            continue

        # نمشي بار بار على نفس symbol أولاً (simplified)
        for ts, row in df.iterrows():
            if not isinstance(ts, datetime):
                ts = pd.to_datetime(ts)
            broker.set_time(ts)
            # تحديث risk من broker
            risk_manager.refresh_from_broker()

            # نبني df_window = كل ما قبل ts (يجب ان يكون لدينا window كافية)
            df_window = df.loc[:ts]
            if len(df_window) < 25:  # window 20 + buffer
                continue

            # 1) Signals
            quant = compute_quant_signals(sym, df_window, window=20)
            nlp = compute_nlp_news_signals(sym)
            social = compute_social_signals(sym)
            composite = build_composite_signal(sym, quant, nlp, social)

            price = float(row["close"])

            # 2) إدارة الصفقات المفتوحة (خروج)
            open_positions = broker.get_open_positions()
            for pos in open_positions:
                if pos.symbol != sym:
                    continue
                # هنا نقدر نستدعي الاستراتيجية الخاصة بنفس pos.strategy_name
                for strat in strategies:
                    if strat.name != pos.strategy_name:
                        continue
                    exit_, reason = strat.should_exit(pos, composite, risk_state)
                    if exit_:
                        pnl = broker.close_position(pos, price)
                        trade_log.add_trade(
                            BacktestTradeRecord(
                                trade_id=pos.id,
                                symbol=pos.symbol,
                                strategy_name=pos.strategy_name or strat.name,
                                side=pos.side,
                                qty=pos.qty,
                                entry_time=pos.opened_at,
                                exit_time=pos.closed_at or ts,
                                entry_price=pos.entry_price,
                                exit_price=price,
                                realized_pnl=pnl,
                                max_favorable_excursion=0.0,
                                max_adverse_excursion=0.0,
                            )
                        )
                        logger.info(
                            "bt_trade_closed symbol=%s strategy=%s pnl=%.2f",
                            pos.symbol,
                            pos.strategy_name,
                            pnl,
                        )

            # 3) دخول صفقات جديدة
            for strat in strategies:
                enter, reason = strat.should_enter(composite, risk_state)
                if not enter:
                    continue

                # تحديد الاتجاه
                direction = composite.direction
                if direction not in ("long", "short"):
                    continue

                side = "buy" if direction == "long" else "sell"
                qty = strat.position_size(composite, risk_state, price)
                if qty <= 0:
                    continue

                notional = qty * price
                allowed, risk_reason = risk_manager.can_open_trade(sym, notional)
                if not allowed:
                    logger.debug(
                        "bt_trade_blocked symbol=%s strat=%s reason=%s",
                        sym,
                        strat.name,
                        risk_reason,
                    )
                    continue

                # بناء order بسيط
                class BTOrder:
                    def __init__(self, symbol, side, qty, price, strategy_name):
                        self.symbol = symbol
                        self.side = side
                        self.qty = qty
                        self.price = price
                        self.strategy_name = strategy_name

                order = BTOrder(sym, side, qty, price, strat.name)
                broker.submit_order(order)

        # نهاية symbol

    return trade_log


هذا skeleton قوي، والـ Agent يقدر يكيّفه مع classes الفعلية عندك (Order, Position، إلخ).

5️⃣ Metrics & Reports
📄 report.py
# FILE: sagetrade/backtest/report.py

from __future__ import annotations
from typing import Dict, List
import pandas as pd

from sagetrade.backtest.trade_log import BacktestTradeRecord

def compute_equity_curve(trades: List[BacktestTradeRecord], initial_equity: float) -> pd.Series:
    if not trades:
        return pd.Series(dtype=float)

    # sort by exit_time
    trades_sorted = sorted(trades, key=lambda t: t.exit_time)
    equity = initial_equity
    times = []
    values = []

    for t in trades_sorted:
        equity += t.realized_pnl
        times.append(t.exit_time)
        values.append(equity)

    return pd.Series(data=values, index=pd.to_datetime(times), name="equity")


def compute_metrics(trades: List[BacktestTradeRecord], initial_equity: float) -> Dict[str, float]:
    if not trades:
        return {}

    df = pd.DataFrame([{
        "symbol": t.symbol,
        "strategy": t.strategy_name,
        "pnl": t.realized_pnl,
    } for t in trades])

    total_pnl = df["pnl"].sum()
    total_return = total_pnl / initial_equity if initial_equity > 0 else 0.0

    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] < 0]
    win_rate = len(wins) / len(df) if len(df) > 0 else 0.0

    avg_win = wins["pnl"].mean() if len(wins) > 0 else 0.0
    avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0.0

    equity_curve = compute_equity_curve(trades, initial_equity)
    if equity_curve.empty:
        max_dd = 0.0
    else:
        peak = equity_curve.cummax()
        dd = (equity_curve - peak)
        max_dd = dd.min()

    return {
        "total_pnl": float(total_pnl),
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "max_drawdown": float(max_dd),
        "num_trades": float(len(df)),
    }


def summarize_by_strategy(trades: List[BacktestTradeRecord]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "strategy": t.strategy_name,
        "pnl": t.realized_pnl,
    } for t in trades])

    return df.groupby("strategy").agg(
        total_pnl=("pnl", "sum"),
        num_trades=("pnl", "count"),
        avg_pnl=("pnl", "mean"),
    )


def summarize_by_symbol(trades: List[BacktestTradeRecord]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "symbol": t.symbol,
        "pnl": t.realized_pnl,
    } for t in trades])

    return df.groupby("symbol").agg(
        total_pnl=("pnl", "sum"),
        num_trades=("pnl", "count"),
        avg_pnl=("pnl", "mean"),
    )

6️⃣ سكربت CLI: scripts/backtest.py

Structure بسيطة:

# FILE: scripts/backtest.py

#!/usr/bin/env python3
import argparse
from datetime import datetime, date

from sagetrade.backtest.runner import run_backtest
from sagetrade.backtest.report import compute_metrics, summarize_by_strategy, summarize_by_symbol
from sagetrade.backtest.trade_log import TradeLog
from sagetrade.utils.logging import setup_logging

import pandas as pd
import pathlib
import json

def load_history_from_files(symbol: str, start: date, end: date) -> pd.DataFrame:
    # هنا تستخدم نفس شكل ملفاتك data/market/YYYY-MM-DD/SYMBOL.jsonl
    # هذا مجرد skeleton
    rows = []
    root = pathlib.Path("data/market")
    current = start
    while current <= end:
        folder = root / current.strftime("%Y-%m-%d")
        path = folder / f"{symbol}.jsonl"
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    rows.append(row)
        current = date.fromordinal(current.toordinal() + 1)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # تأكد من وجود timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    return df

def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols, e.g. BTCUSD,AAPL,EURUSD")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--initial-equity", type=float, default=10000.0)
    parser.add_argument("--out-dir", default="reports/backtests")
    args = parser.parse_args()

    setup_logging()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    start_d = parse_date(args.start)
    end_d = parse_date(args.end)

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trade_log = run_backtest(
        symbols=symbols,
        start=start_d,
        end=end_d,
        initial_equity=args.initial_equity,
        load_history_fn=load_history_from_files,
    )

    # حفظ النتائج
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    trades_path = out_dir / f"trades_{timestamp}.csv"
    summary_path = out_dir / f"summary_{timestamp}.json"

    trade_log.to_csv(str(trades_path))

    metrics = compute_metrics(trade_log.trades, args.initial_equity)
    by_strat = summarize_by_strategy(trade_log.trades)
    by_symbol = summarize_by_symbol(trade_log.trades)

    summary = {
        "metrics": metrics,
        "by_strategy": by_strat.to_dict(orient="index"),
        "by_symbol": by_symbol.to_dict(orient="index"),
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Backtest done for symbols={symbols}")
    print(f"Trades CSV: {trades_path}")
    print(f"Summary JSON: {summary_path}")

if __name__ == "__main__":
    main()

7️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 11 في المشروع

انسخ هذا الـ prompt كما هو للـ Agent (أو لي في جلسة جديدة على نفس الريبو):

You are a senior quant engineer working on my project SAGE SmartTrade.

CONTEXT:
- The project already has:
  - Live/paper trading loop.
  - Brokers (paper), RiskManager, Strategies, Signals (CompositeSignal).
  - Market data stored as JSONL per day in data/market/YYYY-MM-DD/SYMBOL.jsonl (OHLCV).

I now want to implement Phase 11: Backtesting & Performance Reporting.

TASK:

1) Create a simple trade log model.

   - File: `sagetrade/backtest/trade_log.py`
   - Define a `BacktestTradeRecord` dataclass with fields:
     - trade_id: str
     - symbol: str
     - strategy_name: str
     - side: str ("long" or "short")
     - qty: float
     - entry_time: datetime
     - exit_time: datetime
     - entry_price: float
     - exit_price: float
     - realized_pnl: float
     - max_favorable_excursion: float
     - max_adverse_excursion: float
   - Define a `TradeLog` class that:
     - stores a list of `BacktestTradeRecord`.
     - has `add_trade(record)` and `to_csv(path)` methods.

2) Implement a `BacktestBroker`.

   - File: `sagetrade/brokers/backtest.py`
   - Implement a `BacktestPosition` dataclass with:
     - id, symbol, side, qty, entry_price, opened_at, closed_at, realized_pnl, strategy_name, meta.
   - Implement `BacktestBroker(BrokerBase)` with:
     - constructor `__init__(initial_equity: float)`.
     - `set_time(ts: datetime)` to set the current backtest timestamp.
     - `submit_order(order)` that:
       - assumes immediate fill at `order.price`.
       - creates a `BacktestPosition` and updates cash/equity.
     - `close_position(position, price) -> float` computing realized PnL and updating equity/cash.
     - `get_open_positions()`.
     - `get_account_summary()` returning:
       - balance, equity, realized_pnl, open_positions, open_notional, per_symbol_notional.
   - Keep the first version simple (no complex slippage or fees).

3) Implement the backtest runner.

   - File: `sagetrade/backtest/runner.py`
   - Implement a function:

     `run_backtest(symbols: list[str], start: date, end: date, initial_equity: float, load_history_fn) -> TradeLog`

     that:
     - Instantiates `BacktestBroker(initial_equity)` and initializes `RiskState` & `RiskManager`.
     - For each symbol:
       - Calls `load_history_fn(symbol, start, end)` to get a pandas DataFrame with OHLCV and timestamps.
       - Iterates bar by bar:
         - Calls `broker.set_time(ts)`.
         - Calls `risk_manager.refresh_from_broker()`.
         - Builds a window `df_window` up to current ts for signals.
         - Computes:
           - `QuantSignals` via `compute_quant_signals`.
           - news and social signals via the existing placeholder functions.
           - `CompositeSignal` via `build_composite_signal`.
         - Manages open positions:
           - For each open position for that symbol:
             - Finds its strategy.
             - Calls `strategy.should_exit(position, composite, risk_state)`.
             - If exit=True, closes the position at current close price, adds a `BacktestTradeRecord` to `TradeLog`.
         - Handles entries:
           - For each enabled strategy for that symbol:
             - Calls `strategy.should_enter(composite, risk_state)`.
             - If enter=True:
               - Determine direction from `CompositeSignal`.
               - Compute `qty = strategy.position_size(composite, risk_state, price)`.
               - Compute `notional = qty * price`.
               - Call `risk_manager.can_open_trade(symbol, notional)`.
               - If allowed, create a simple order object with attributes (symbol, side, qty, price, strategy_name) and call `broker.submit_order(order)`.

4) Implement reporting helpers.

   - File: `sagetrade/backtest/report.py`
   - Functions:
     - `compute_equity_curve(trades: list[BacktestTradeRecord], initial_equity: float) -> pd.Series`
       - Sort trades by exit_time and accumulate equity over time.
     - `compute_metrics(trades, initial_equity) -> dict` that returns:
       - total_pnl, total_return, win_rate, avg_win, avg_loss, max_drawdown, num_trades.
     - `summarize_by_strategy(trades) -> pd.DataFrame`:
       - grouped stats per strategy.
     - `summarize_by_symbol(trades) -> pd.DataFrame`:
       - grouped stats per symbol.

5) Create a CLI backtest script.

   - File: `scripts/backtest.py`
   - Arguments:
     - `--symbols` (comma separated)
     - `--start` (YYYY-MM-DD)
     - `--end` (YYYY-MM-DD)
     - `--initial-equity` (float, default 10000)
     - `--out-dir` (default "reports/backtests")
   - Implement a `load_history_from_files(symbol, start, end)` helper that:
     - Reads JSONL files from `data/market/YYYY-MM-DD/SYMBOL.jsonl`.
     - Returns a DataFrame with timestamp and OHLCV sorted by time.
   - Call `run_backtest(...)` with this loader.
   - Save:
     - `trades_<timestamp>.csv` via `TradeLog.to_csv`.
     - `summary_<timestamp>.json` with global metrics + per-strategy + per-symbol stats.

STYLE:
- Use Python 3.11+ typing and dataclasses.
- Integrate with existing logging via `get_logger`.
- Make sure backtest runner uses the same RiskManager and strategies as the live system where possible.
- Output changes as code blocks with paths:

  # FILE: sagetrade/backtest/trade_log.py
  ...
  # FILE: sagetrade/brokers/backtest.py
  ...
  # FILE: sagetrade/backtest/runner.py
  ...
  # FILE: sagetrade/backtest/report.py
  ...
  # FILE: scripts/backtest.py
  ...
