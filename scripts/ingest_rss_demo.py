#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.ingestion.news_social import RSSIngestor
from sagetrade.messaging.queue import build_queue_from_env
from sagetrade.storage.sink import TextStorage
from sagetrade.utils.dedupe import TTLSet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", action="append", default=[
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ])
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--store", action="store_true")
    args = parser.parse_args()

    ing = RSSIngestor(args.feed)
    dedupe = TTLSet(ttl_seconds=3600)
    q = build_queue_from_env() if args.publish else None
    storage = TextStorage() if args.store else None

    count = 0
    for item in ing.poll():
        if dedupe.seen(item["id"]):
            continue
        dedupe.add(item["id"])
        count += 1
        if q:
            q.publish("news.rss", item)
        if storage:
            storage.write_item("rss", item)
        print("rss:", item.get("title", "<no-title>")[:80])
    print(f"total items: {count}")


if __name__ == "__main__":
    main()
