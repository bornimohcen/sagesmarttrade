from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def setup_logging(level: int = logging.INFO) -> None:
    """Configure standard library logging (console + file).

    This complements the JSON `log_event` helper and is intended mainly for
    scripts and local development. It is safe to call multiple times.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "sagesmarttrade.log", encoding="utf-8"),
        ],
    )


def log_event(event: str, level: str = "INFO", **fields: Any) -> None:
    """Emit a simple JSON log line to stdout.

    This is intended for sandbox observability and can be shipped to ELK later.
    """
    payload: Dict[str, Any] = {
        "ts": _now_iso(),
        "level": level,
        "event": event,
    }
    payload.update(fields)
    try:
        print(json.dumps(payload, ensure_ascii=False), file=sys.stdout)
    except Exception:
        # Logging must never crash main logic.
        try:
            print(f"[{payload.get('level','INFO')}] {payload.get('event')}", file=sys.stdout)
        except Exception:
            pass


def log_error(event: str, **fields: Any) -> None:
    log_event(event, level="ERROR", **fields)

