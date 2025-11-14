#!/usr/bin/env python3
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.backtest.simple import run_single_symbol_backtest


def load_jsonl(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    symbol = "BTCUSD"

    market_dirs = sorted(glob.glob(os.path.join("data", "market", "*")))
    text_dirs = sorted(glob.glob(os.path.join("data", "text", "*")))
    if not market_dirs or not text_dirs:
        raise SystemExit(
            "Need both market and text data; run ingest_market_sim_demo and ingest_rss_demo first."
        )

    m_last = market_dirs[-1]
    t_last = text_dirs[-1]

    market_path = os.path.join(m_last, f"{symbol}.jsonl")
    text_path = os.path.join(t_last, "rss.jsonl")
    if not os.path.exists(market_path):
        raise SystemExit(f"Missing market file: {market_path}")
    if not os.path.exists(text_path):
        raise SystemExit(f"Missing text file: {text_path}")

    bars = load_jsonl(market_path)
    items = load_jsonl(text_path)

    result = run_single_symbol_backtest(symbol, bars, items, window=20)

    print(f"Backtest for {symbol}")
    print(f"- bars: {len(bars)}")
    print(f"- trades closed: {len(result.trades)}")
    print(f"- total PnL: {result.total_pnl:.4f}")
    print(f"- max drawdown: {result.max_drawdown * 100:.2f}%")


if __name__ == "__main__":
    main()

