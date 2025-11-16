#!/usr/bin/env python3
"""
Fetch historical bars from Alpaca Data API and store them as JSONL in data/market/<YYYY-MM-DD>/<SYMBOL>.jsonl.

Supports stocks via v2/stocks/{symbol}/bars and a best-effort crypto fallback using v1beta1/crypto/{symbol}/bars.
Requires env vars: ALPACA_API_KEY, ALPACA_API_SECRET.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

DATA_HOST = "https://data.alpaca.markets"


def iso_to_ts(iso_str: str) -> float:
    """Convert Alpaca ISO timestamp to unix seconds."""
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def write_jsonl(symbol: str, bars: List[Dict], out_dir: Path, date_dir: Optional[str] = None) -> Path:
    day = date_dir or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target_dir = out_dir / day
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{symbol}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for b in bars:
            f.write(json.dumps(b) + "\n")
    return out_path


def fetch_stock_bars(symbol: str, timeframe: str, start: Optional[str], end: Optional[str], limit: int, headers: Dict[str, str]) -> List[Dict]:
    url = f"{DATA_HOST}/v2/stocks/{symbol}/bars"
    params: Dict[str, object] = {"timeframe": timeframe, "limit": limit}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    page_token: Optional[str] = None
    rows: List[Dict] = []
    fetched = 0
    while True:
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        bars = data.get("bars", [])
        for b in bars:
            rows.append(
                {
                    "ts": iso_to_ts(b.get("t", "")),
                    "o": b.get("o", 0.0),
                    "h": b.get("h", 0.0),
                    "l": b.get("l", 0.0),
                    "c": b.get("c", 0.0),
                    "v": b.get("v", 0.0),
                }
            )
            fetched += 1
            if fetched >= limit:
                return rows
        page_token = data.get("next_page_token")
        if not page_token:
            break
    rows = []
    return rows


def fetch_crypto_bars(symbol: str, timeframe: str, start: Optional[str], end: Optional[str], limit: int, headers: Dict[str, str]) -> List[Dict]:
    """Fetch crypto bars from Alpaca v1beta3 crypto/us/bars using symbols=BASE/QUOTE."""
    if "/" not in symbol and len(symbol) > 3:
        symbol = symbol[:-3] + "/" + symbol[-3:]
    url = f"{DATA_HOST}/v1beta3/crypto/us/bars"
    params: Dict[str, object] = {"timeframe": timeframe, "limit": limit, "symbols": symbol}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    rows: List[Dict] = []
    fetched = 0
    page_token: Optional[str] = None
    while True:
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        raw = resp.json().get("bars", {})
        bars_list: List[Dict] = []
        if isinstance(raw, dict):
            for _, sym_bars in raw.items():
                bars_list.extend(sym_bars)
        elif isinstance(raw, list):
            bars_list = raw

        for b in bars_list:
            rows.append(
                {
                    "ts": iso_to_ts(b.get("t", "")),
                    "o": b.get("o", 0.0),
                    "h": b.get("h", 0.0),
                    "l": b.get("l", 0.0),
                    "c": b.get("c", 0.0),
                    "v": b.get("v", 0.0),
                }
            )
            fetched += 1
            if fetched >= limit:
                return rows
        page_token = resp.json().get("next_page_token")
        if not page_token:
            break
    return rows


def fetch_fx_bars(symbol: str, timeframe: str, start: Optional[str], end: Optional[str], limit: int, headers: Dict[str, str]) -> List[Dict]:
    """Fetch FX rates/bars from Alpaca forex rates endpoint v1beta1/forex/rates using symbols param."""
    url = f"{DATA_HOST}/v1beta1/forex/rates"
    params: Dict[str, object] = {"symbols": symbol, "timeframe": timeframe, "limit": limit}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 403:
        raise RuntimeError("403 from forex/rates – FX data not enabled for this Alpaca account/plan.")
    resp.raise_for_status()
    data = resp.json().get("rates", [])
    rows: List[Dict] = []
    for b in data:
        rows.append(
            {
                "ts": iso_to_ts(b.get("t", "")),
                "o": b.get("o", 0.0),
                "h": b.get("h", 0.0),
                "l": b.get("l", 0.0),
                "c": b.get("c", 0.0),
                "v": b.get("v", 0.0),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch historical bars from Alpaca and store as JSONL.")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols, e.g., AAPL,BTCUSD,EURUSD")
    parser.add_argument("--timeframe", default="1Min", help="Alpaca timeframe, e.g., 1Min, 5Min, 1Hour, 1Day")
    parser.add_argument("--start", help="ISO start time, e.g., 2024-01-01T00:00:00Z")
    parser.add_argument("--end", help="ISO end time, optional")
    parser.add_argument("--limit", type=int, default=1000, help="Max bars to fetch")
    parser.add_argument("--out-dir", default="data/market", help="Base output dir")
    args = parser.parse_args()

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in environment.")

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json",
    }

    out_base = Path(args.out_dir)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("No symbols provided.")

    # Common FX majors to route to forex endpoint.
    fx_majors = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY"}

    for sym in symbols:
        try:
            bars: List[Dict] = []
            # Routing:
            # - FX: explicit majors only
            # - Stocks: alphabetic <=5 and not FX
            # - Crypto: 6-letter ending with USD (e.g., BTCUSD), otherwise fallback to crypto
            if sym in fx_majors:
                try:
                    bars = fetch_fx_bars(sym, args.timeframe, args.start, args.end, args.limit, headers)
                except RuntimeError as fx_err:
                    print(f"[{sym}] skipped – forex not enabled: {fx_err}")
                    continue
            elif sym.isalpha() and 1 <= len(sym) <= 5 and sym not in fx_majors:
                bars = fetch_stock_bars(sym, args.timeframe, args.start, args.end, args.limit, headers)
            elif len(sym) == 6 and sym.isalpha() and sym.endswith("USD"):
                bars = fetch_crypto_bars(sym, args.timeframe, args.start, args.end, args.limit, headers)
            else:
                print(f"[{sym}] skipped – unsupported symbol format.")
                continue
            if not bars:
                print(f"[{sym}] no bars fetched.")
                continue
            out_path = write_jsonl(sym, bars, out_base)
            print(f"[{sym}] fetched {len(bars)} bars -> {out_path}")
        except Exception as exc:
            print(f"[{sym}] fetch failed: {exc}")
            continue

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
