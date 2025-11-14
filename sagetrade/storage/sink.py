import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _today_dir(base: str) -> str:
    d = datetime.utcnow().strftime("%Y-%m-%d")
    p = os.path.join(base, d)
    _ensure_dir(p)
    return p


def write_jsonl(path: str, record: Dict[str, Any]) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class MarketStorage:
    """Stores market data daily under data/market/YYYY-MM-DD/*.jsonl or parquet if available."""

    def __init__(self, base_dir: str = "data/market") -> None:
        self.base_dir = base_dir
        self._parquet_available = False
        try:
            import pyarrow  # type: ignore
            self._parquet_available = True
        except Exception:
            self._parquet_available = False

    def write_bar(self, symbol: str, bar: Dict[str, Any]) -> None:
        day_dir = _today_dir(self.base_dir)
        if self._parquet_available:
            # Fallback to JSONL for now; parquet batching requires more handling.
            # To enable parquet, implement arrow Table batching here.
            path = os.path.join(day_dir, f"{symbol}.jsonl")
        else:
            path = os.path.join(day_dir, f"{symbol}.jsonl")
        write_jsonl(path, bar)


class TextStorage:
    """Stores raw text + metadata for news/social under data/text/YYYY-MM-DD/*.jsonl"""

    def __init__(self, base_dir: str = "data/text") -> None:
        self.base_dir = base_dir

    def write_item(self, source: str, item: Dict[str, Any]) -> None:
        day_dir = _today_dir(self.base_dir)
        path = os.path.join(day_dir, f"{source}.jsonl")
        write_jsonl(path, item)

