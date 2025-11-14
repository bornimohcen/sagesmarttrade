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

from sagetrade.signals.nlp import get_signals


def load_items(path: str, limit: int) -> list:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items[-limit:] if limit > 0 else items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity", default="market")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    day_dirs = sorted(glob.glob(os.path.join("data", "text", "*")))
    if not day_dirs:
        raise SystemExit("no data/text found; run ingest_rss_demo first")
    last_dir = day_dirs[-1]
    path = os.path.join(last_dir, "rss.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"file not found: {path}")

    items = load_items(path, args.limit)
    sig = get_signals(args.entity, items)
    print("NLP signals:", sig)


if __name__ == "__main__":
    main()
