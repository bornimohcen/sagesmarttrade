import hashlib
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, Iterator, List


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


class RSSIngestor:
    """Simple RSS ingestor using stdlib only (no feedparser).

    Limitations: assumes typical RSS 2.0 structure. Good enough for MVP and tests.
    """

    def __init__(self, feeds: List[str]):
        self.feeds = feeds

    def poll(self) -> Iterator[Dict]:
        now = time.time()
        for url in self.feeds:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = resp.read()
                root = ET.fromstring(data)
                # RSS 2.0: channel/item
                for item in root.findall("channel/item"):
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    guid = (item.findtext("guid") or link or title)
                    desc = (item.findtext("description") or "")
                    pub = item.findtext("pubDate") or ""
                    yield {
                        "source": "rss",
                        "url": url,
                        "guid": guid,
                        "id": _hash(guid or link or title),
                        "title": title,
                        "link": link,
                        "description": desc,
                        "published": pub,
                        "ts": now,
                    }
            except Exception as e:
                # Log and skip faulty feeds so it is visible when nothing is ingested.
                print(f"RSSIngestor: failed to ingest from {url}: {e}", file=sys.stderr)
                continue
