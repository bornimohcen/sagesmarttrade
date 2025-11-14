#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.env import load_env_file
from sagetrade.brokers.alpaca_assets import AlpacaAssetsClient


def main() -> None:
    # Ensure env vars are loaded (BROKER_API_KEY, BROKER_API_SECRET, BROKER_BASE_URL).
    load_env_file("config/secrets.env")

    client = AlpacaAssetsClient()
    print("Fetching tradable assets from Alpaca...")
    assets = client.list_assets(status="active", asset_class=None)

    symbols: dict[str, dict] = {}
    for a in assets:
        if not a.tradable:
            continue

        # Normalize asset_class to a lowercase string.
        raw_ac = getattr(a, "asset_class", "") or ""
        asset_class_str = str(raw_ac).lower()

        # Map Alpaca asset_class to our generic classes/venues.
        if asset_class_str == "crypto":
            asset_class = "crypto"
            venue = "alpaca-crypto"
            min_qty = 0.0001
            max_leverage = 2.0
        elif asset_class_str == "us_equity":
            asset_class = "equity"
            venue = "alpaca-equity"
            # Allow fractional; exact minimum may depend on plan, so keep small default.
            min_qty = 0.0001
            max_leverage = 1.0
        else:
            asset_class = asset_class_str or "unknown"
            venue = f"alpaca-{asset_class}"
            min_qty = 1.0
            max_leverage = 1.0

        symbols[a.symbol] = {
            "asset_class": asset_class,
            "venue": venue,
            "min_qty": min_qty,
            "max_leverage": max_leverage,
            "exchange": a.exchange,
        }

    universe = {"symbols": symbols}

    config_dir = ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    out_path = config_dir / "universe.json"
    out_path.write_text(json.dumps(universe, indent=2), encoding="utf-8")

    print(f"Universe updated: {len(symbols)} tradable symbols written to {out_path}")


if __name__ == "__main__":
    main()
