#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.backtest.data_loader import load_jsonl
from sagetrade.backtest.report import compute_metrics, summarize_by_strategy, summarize_by_symbol
from sagetrade.backtest.runner import run_backtest
from sagetrade.backtest.trade_log import TradeLog
from sagetrade.utils.logging import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a simple backtest over stored JSONL bars.")
    parser.add_argument("--symbols", default="BTCUSD", help="Comma-separated list of symbols.")
    parser.add_argument("--window", type=int, default=20, help="Window size for quant signals.")
    parser.add_argument("--initial-equity", type=float, default=10_000.0, help="Starting equity.")
    parser.add_argument("--market-dir", default="data/market", help="Base directory for market data.")
    parser.add_argument("--text-file", default=None, help="Path to news/text JSONL (optional).")
    parser.add_argument("--out-dir", default="reports", help="Output directory for reports.")
    args = parser.parse_args()

    setup_logging()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("No symbols provided.")

    base = Path(args.market_dir)
    if not base.exists():
        raise SystemExit(f"Market dir not found: {base}")

    news_items = []
    if args.text_file:
        news_items = load_jsonl(args.text_file, limit=None)

    combined_log = TradeLog()

    for sym in symbols:
        day_dirs: List[Path] = sorted([p for p in base.glob("*") if p.is_dir()])
        if not day_dirs:
            print(f"[{sym}] no day dirs under {base}")
            continue
        latest = day_dirs[-1]
        market_path = latest / f"{sym}.jsonl"
        bars = load_jsonl(market_path, limit=None)
        if not bars:
            print(f"[{sym}] no bars at {market_path}")
            continue

        log = run_backtest(sym, bars, news_items, initial_equity=args.initial_equity, window=args.window)
        for t in log.trades:
            combined_log.add_trade(t)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    trades_csv = out_dir / "trades.csv"
    combined_log.to_csv(trades_csv)

    metrics = compute_metrics(combined_log.trades, args.initial_equity)
    strat_summary = summarize_by_strategy(combined_log.trades)
    sym_summary = summarize_by_symbol(combined_log.trades)

    # Write simple summaries
    with (out_dir / "summary.txt").open("w", encoding="utf-8") as f:
        f.write(f"Total trades: {len(combined_log.trades)}\n")
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")
        f.write("\nPer-strategy:\n")
        f.write(str(strat_summary))
        f.write("\n\nPer-symbol:\n")
        f.write(str(sym_summary))

    print(f"Backtest finished. Trades: {len(combined_log.trades)}")
    print(f"- trades csv: {trades_csv}")
    print(f"- summary: {out_dir / 'summary.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

