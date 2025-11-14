#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.messaging.queue import build_queue_from_env


def main():
    q = build_queue_from_env()
    print("Consuming topic demo.test ... Press Ctrl+C to exit")
    for msg in q.consume("demo.test", timeout_ms=2000):
        print("got:", msg)


if __name__ == "__main__":
    main()
