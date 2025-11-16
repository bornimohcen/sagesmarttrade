from __future__ import annotations

"""Minimal stub for a future web dashboard API.

If FastAPI is installed, this exposes a tiny app with a health-check
endpoint so the rest of the system can start wiring integrations to it.
Otherwise, `app` is set to None.
"""

from typing import Any, Dict

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None  # type: ignore[assignment]


if FastAPI is not None:
    app = FastAPI(title="SAGE SmartTrade Dashboard")

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}
else:
    app = None


__all__ = ["app"]

