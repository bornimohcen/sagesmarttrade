#!/usr/bin/env python3
import os
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.messaging.queue import build_queue_from_env


def main():
    q = build_queue_from_env()
    for i in range(10):
        q.publish("demo.test", {"i": i, "ts": time.time()})
        print("published", i)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
