from __future__ import annotations

import json
import logging
import sys
import time
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Optional

from sagetrade.utils.config import get_settings


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def setup_logging(level: int = logging.INFO, *, log_to_file: bool = True) -> None:
    """Configure root logging for SAGE SmartTrade.

    - Console output with a readable format.
    - Optional file output in logs/sagesmarttrade.log.
    - Safe to call multiple times.
    """
    settings = get_settings()
    logs_dir = Path(settings.data.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    handlers: list[logging.Handler] = []

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(console_handler)

    if log_to_file:
        file_handler = logging.FileHandler(logs_dir / "sagesmarttrade.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)

    # Reduce noise from common third-party libraries.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> Logger:
    """Return a namespaced logger."""
    return logging.getLogger(name or "sagetrade")


def log_event(event: str, level: str = "INFO", **fields: Any) -> None:
    """Emit a simple JSON log line to stdout.

    This is intended for structured observability and can be shipped to ELK later.
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
