#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.kill_switch import is_enabled as kill_switch_enabled
from sagetrade.execution.paper_broker import PaperBroker
from sagetrade.risk.manager import RiskManager
from sagetrade.signals.aggregator import aggregate
from sagetrade.signals.nlp import get_signals as get_nlp_signals
from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.strategy.registry import StrategyManager
from sagetrade.utils.logging import log_event


def load_jsonl(path: str, limit: int = 0) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        return []
    if limit > 0:
        return rows[-limit:]
    return rows


def find_latest_day_dir(base: str) -> str:
    dirs = sorted(glob.glob(os.path.join(base, "*")))
    return dirs[-1] if dirs else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous paper-trading loop over stored market/text data.")
    parser.add_argument(
        "--symbols",
        default="BTCUSD",
        help="Comma-separated list of symbols to trade.",
    )
    parser.add_argument("--window", type=int, default=20, help="Window size for quant signals.")
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=5.0,
        help="Seconds to sleep between iterations.",
    )
    parser.add_argument(
        "--account-id",
        default="paper-loop",
        help="Paper account id for trade history segregation.",
    )
    parser.add_argument(
        "--bars-limit",
        type=int,
        default=500,
        help="Max number of recent bars to use per symbol.",
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("No symbols provided.")

    market_day_dir = find_latest_day_dir(os.path.join("data", "market"))
    text_day_dir = find_latest_day_dir(os.path.join("data", "text"))
    if not market_day_dir or not text_day_dir:
        raise SystemExit(
            "Need both market and text data; run ingest_market_sim_demo and ingest_rss_demo first."
        )

    text_path = os.path.join(text_day_dir, "rss.jsonl")
    if not os.path.exists(text_path):
        raise SystemExit(f"Missing text file: {text_path}")

    news_items = load_jsonl(text_path)
    if not news_items:
        raise SystemExit(f"No news items found in {text_path}")

    # NLP signals remain relatively stable over the recent window; compute once.
    nlp_sig = get_nlp_signals("market", news_items)

    risk = RiskManager()
    broker = PaperBroker(initial_balance=risk.cfg.initial_equity, account_id=args.account_id)
    manager = StrategyManager()

    log_event(
        "paper_trade_loop_started",
        symbols=symbols,
        account_id=args.account_id,
        window=args.window,
    )
    print(f"Paper-trade loop started for symbols={symbols}, account_id={args.account_id}. Press Ctrl+C to stop.")

    try:
        while True:
            if kill_switch_enabled():
                print("Kill-switch ENABLED: skipping new trades this iteration.")
            market_day_dir = find_latest_day_dir(os.path.join("data", "market"))
            if not market_day_dir:
                print("No market day directory found under data/market; sleeping...")
                time.sleep(args.sleep_sec)
                continue

            price_by_symbol: Dict[str, float] = {}

            for symbol in symbols:
                market_path = os.path.join(market_day_dir, f"{symbol}.jsonl")
                bars = load_jsonl(market_path, limit=args.bars_limit)
                if not bars:
                    print(f"[{symbol}] no bars found at {market_path}; skipping.")
                    continue

                current_price = float(bars[-1]["c"])
                price_by_symbol[symbol] = current_price

                if len(bars) < args.window:
                    print(f"[{symbol}] not enough bars for window={args.window}; got={len(bars)}.")
                    continue

                # Do not open new trades if there is already open exposure for this symbol.
                if risk.state.open_notional_by_symbol.get(symbol, 0.0) > 0.0:
                    print(f"[{symbol}] open exposure exists, skipping new entries this iteration.")
                    continue

                q_sig = get_signals_from_bars(symbol, bars, window=args.window)
                comp = aggregate(symbol, q_sig, nlp_sig)

                print(f"[{symbol}] Composite signal: {comp}")

                if kill_switch_enabled():
                    continue

                strategies = manager.select_for_signal(comp)
                print(f"[{symbol}] Active strategies:", [s.name for s in strategies])

                for strat in strategies:
                    decision = strat.on_new_signal(comp)
                    if decision is None:
                        print(f"[{symbol}] {strat.name}: no trade decision.")
                        continue

                    allowed, reason = risk.can_open(decision, current_price)
                    if not allowed:
                        print(f"[{symbol}] {strat.name}: BLOCKED by risk manager ({reason}).")
                        continue

                    order, position = broker.execute_decision(decision, current_price)
                    risk.on_open(decision, current_price)
                    print(f"[{symbol}] {strat.name}: ORDER -> {order}")
                    print(f"[{symbol}] {strat.name}: POSITION -> {position}")

            # Evaluate TP/SL across all symbols using current prices.
            if price_by_symbol:
                closed_map = broker.check_tp_sl(price_by_symbol)
                for pos_id, (closed, notional) in closed_map.items():
                    risk.on_close(closed.symbol, notional, closed.realized_pnl)
                    print(f"[CLOSE] {pos_id}: {closed}")

            summary = broker.summary()
            # Synchronize risk state with broker account summary for equity/PnL.
            risk.state.equity = summary.get("equity", risk.state.equity)
            risk.state.realized_pnl = summary.get("realized_pnl", risk.state.realized_pnl)

            print("Risk state:", risk.state)
            print("Broker summary:", summary)
            log_event(
                "paper_trade_loop_iteration",
                account_id=args.account_id,
                equity=risk.state.equity,
                realized_pnl=risk.state.realized_pnl,
                open_trades=risk.state.open_trades,
            )
            time.sleep(args.sleep_sec)
    except KeyboardInterrupt:
        print("\nPaper-trade loop stopped by user.")
        log_event("paper_trade_loop_stopped", account_id=args.account_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
