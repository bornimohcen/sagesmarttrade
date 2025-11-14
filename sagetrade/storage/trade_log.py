from __future__ import annotations

import json
import os
from typing import Any, Dict, List


TRADE_LOG_DIR = os.path.join("runtime", "trades")


def _ensure_dir() -> None:
    os.makedirs(TRADE_LOG_DIR, exist_ok=True)


def _account_path(account_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in account_id)
    return os.path.join(TRADE_LOG_DIR, f"{safe}.jsonl")


def append_trade(account_id: str, trade: Dict[str, Any]) -> None:
    """Append a single trade record to the JSONL file for this account."""
    _ensure_dir()
    path = _account_path(account_id)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trade, ensure_ascii=False) + "\n")
    except Exception:
        # Trade logging must not break the main flow.
        return


def load_trades(account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Load up to `limit` most recent trades for an account from disk."""
    path = _account_path(account_id)
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    if limit > 0:
        return rows[-limit:]
    return rows

