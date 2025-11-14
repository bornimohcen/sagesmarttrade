#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.signals.quant import get_signals_from_bars


def load_bars(path: str, limit: int) -> list:
    bars = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bars.append(json.loads(line))
    return bars[-limit:] if limit > 0 else bars


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    day_dirs = sorted(glob.glob(os.path.join("data", "market", "*")))
    if not day_dirs:
        raise SystemExit("no data/market found; run ingest_market_sim_demo first")
    last_dir = day_dirs[-1]
    path = os.path.join(last_dir, f"{args.symbol}.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"file not found: {path}")

    bars = load_bars(path, args.limit)
    sig = get_signals_from_bars(args.symbol, bars, window=args.window)
    print("Quant signals:", sig)


if __name__ == "__main__":
    main()
