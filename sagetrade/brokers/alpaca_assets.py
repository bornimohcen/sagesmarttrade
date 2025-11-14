from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sagetrade.utils.retry import retry


@dataclass
class AlpacaAsset:
    symbol: str
    name: str
    asset_class: str  # us_equity, crypto, etc.
    exchange: str
    tradable: bool
    marginable: bool
    shortable: bool
    easy_to_borrow: bool


class AlpacaAssetsClient:
    """Minimal Alpaca Assets API client using stdlib only.

    Uses environment variables:
    - BROKER_BASE_URL (defaults to https://paper-api.alpaca.markets)
    - BROKER_API_KEY
    - BROKER_API_SECRET
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        raw_base = base_url or os.environ.get("BROKER_BASE_URL") or "https://paper-api.alpaca.markets"
        # Normalize: users sometimes include `/v2` in the base URL; the assets endpoint already appends `/v2/`.
        raw_base = raw_base.rstrip("/")
        if raw_base.endswith("/v2"):
            raw_base = raw_base[: -len("/v2")]
        self.base_url = raw_base
        self.key_id = os.environ.get("BROKER_API_KEY") or os.environ.get("APCA_API_KEY_ID")
        self.secret_key = os.environ.get("BROKER_API_SECRET") or os.environ.get("APCA_API_SECRET_KEY")
        if not self.key_id or not self.secret_key:
            raise RuntimeError("BROKER_API_KEY / BROKER_API_SECRET (or APCA_API_KEY_ID / APCA_API_SECRET_KEY) must be set.")

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
        }

    @retry(max_attempts=3, backoff_seconds=2.0)
    def list_assets(self, status: str = "active", asset_class: Optional[str] = None) -> List[AlpacaAsset]:
        params: Dict[str, Any] = {"status": status}
        if asset_class:
            params["asset_class"] = asset_class
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}/v2/assets?{query}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assets: List[AlpacaAsset] = []
        for a in data:
            assets.append(
                AlpacaAsset(
                    symbol=a.get("symbol", ""),
                    name=a.get("name", ""),
                    # Alpaca REST uses field name "class" for asset class; keep "asset_class" as fallback.
                    asset_class=a.get("class") or a.get("asset_class", ""),
                    exchange=a.get("exchange", ""),
                    tradable=bool(a.get("tradable", False)),
                    marginable=bool(a.get("marginable", False)),
                    shortable=bool(a.get("shortable", False)),
                    easy_to_borrow=bool(a.get("easy_to_borrow", False)),
                )
            )
        return assets
