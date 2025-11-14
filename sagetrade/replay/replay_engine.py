import glob
import json
import os
import time
from typing import Iterator

from sagetrade.messaging.queue import MessageQueue


def read_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def replay_market_day(day_dir: str, queue: MessageQueue, topic: str = "market.bars", speed: float = 1.0) -> None:
    files = sorted(glob.glob(os.path.join(day_dir, "*.jsonl")))
    for fp in files:
        for rec in read_jsonl(fp):
            queue.publish(topic, rec)
            if speed > 0:
                time.sleep(0.001 / speed)

