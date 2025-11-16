from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import json
import pandas as pd


def load_jsonl(path: str | Path, limit: int | None = None) -> List[dict]:
    """Load JSONL file into list of dicts (optionally trimmed to last N)."""
    rows: List[dict] = []
    p = Path(path)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


def to_dataframe(bars: Iterable[dict]) -> pd.DataFrame:
    """Convert iterable of bar dicts to pandas DataFrame with standard columns."""
    df = pd.DataFrame(list(bars))
    # Normalize column names
    col_map = {
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
        "ts": "timestamp",
    }
    for src, dst in col_map.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]
    if "timestamp" not in df.columns and "time" in df.columns:
        df["timestamp"] = df["time"]
    if "timestamp" not in df.columns:
        df["timestamp"] = range(len(df))
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


__all__ = ["load_jsonl", "to_dataframe"]

