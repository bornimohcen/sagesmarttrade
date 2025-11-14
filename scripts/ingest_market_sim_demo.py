#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.ingestion.market_fetcher import SimulatedMarketFetcher
from sagetrade.messaging.queue import build_queue_from_env
from sagetrade.storage.sink import MarketStorage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--interval", type=float, default=0.05, help="seconds between bars")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--store", action="store_true")
    args = parser.parse_args()

    fetcher = SimulatedMarketFetcher(symbol=args.symbol)
    q = build_queue_from_env() if args.publish else None
    storage = MarketStorage() if args.store else None

    for bar in fetcher.stream(interval_sec=args.interval):
        if q:
            q.publish("market.bars", bar)
        if storage:
            storage.write_bar(args.symbol, bar)
        print("bar", bar["symbol"], bar["c"])  # brief output


if __name__ == "__main__":
    main()
