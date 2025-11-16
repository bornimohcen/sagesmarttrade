#!/usr/bin/env python3
"""
Very simple strategy runner using Alpaca (paper/live depending on config).

Behavior:
- Fetches latest bars for each symbol from Alpaca Data API (stocks or crypto).
- Computes quant + NLP placeholders + composite signals.
- Passes signals to registered strategies.
- Uses RiskManager to gate entries.
- Sends market orders via broker_factory (PaperBroker or AlpacaBroker depending on config).

WARNING: If config.brokers.default = "alpaca" and keys point to live trading,
this can place live market orders. Use paper credentials/base_url for safety.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.execution.broker_factory import build_broker
from sagetrade.risk.manager import RiskManager
from sagetrade.signals.aggregator import build_composite_signal
from sagetrade.signals.nlp_news import compute_nlp_news_signals
from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.signals.social import compute_social_signals
from sagetrade.strategy.registry import StrategyManager
from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger, setup_logging


logger = get_logger(__name__)
DATA_HOST = "https://data.alpaca.markets"


def iso_now_minus(minutes: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_recent_stock_bars(symbol: str, timeframe: str, limit: int, headers: Dict[str, str]) -> List[dict]:
    url = f"{DATA_HOST}/v2/stocks/{symbol}/bars"
    params = {"timeframe": timeframe, "limit": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    bars = resp.json().get("bars", [])
    return [{"ts": b["t"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b.get("v", 0)} for b in bars]


def fetch_recent_crypto_bars(symbol: str, timeframe: str, limit: int, headers: Dict[str, str]) -> List[dict]:
    if "/" not in symbol and len(symbol) > 3:
        symbol = symbol[:-3] + "/" + symbol[-3:]
    url = f"{DATA_HOST}/v1beta3/crypto/us/bars"
    params = {"timeframe": timeframe, "limit": limit, "symbols": symbol}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json().get("bars", {})
    bars = []
    if isinstance(raw, dict):
        for _, sym_bars in raw.items():
            bars.extend(sym_bars)
    return [{"ts": b["t"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b.get("v", 0)} for b in bars]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple Alpaca strategy runner (paper/live depending on config).")
    parser.add_argument("--symbols", help="Comma-separated symbols; default from settings.symbols.default_universe")
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--limit", type=int, default=100, help="Number of recent bars to fetch")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    symbols = [s.strip().upper() for s in (args.symbols.split(",") if args.symbols else settings.symbols.default_universe)]

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("ALPACA_API_KEY/ALPACA_API_SECRET must be set for Alpaca data.")
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json",
    }

    broker = build_broker()
    risk = RiskManager()
    strat_mgr = StrategyManager()

    for sym in symbols:
        try:
            if sym.isalpha() and len(sym) <= 5:
                bars = fetch_recent_stock_bars(sym, args.timeframe, args.limit, headers)
            else:
                bars = fetch_recent_crypto_bars(sym, args.timeframe, args.limit, headers)
            if len(bars) < 20:
                logger.warning("[%s] not enough bars fetched; skipping", sym)
                continue

            nlp_sig = compute_nlp_news_signals("market")
            social_sig = compute_social_signals(sym)
            q_sig = get_signals_from_bars(sym, bars, window=20)
            comp = build_composite_signal(sym, q_sig, nlp_sig, social_sig)

            strategies = strat_mgr.select_for_signal(comp)
            for strat in strategies:
                decision = strat.on_new_signal(comp)
                if decision is None:
                    continue
                current_price = float(bars[-1]["c"])
                allowed, reason = risk.can_open(decision, current_price)
                if not allowed:
                    logger.info("[%s] %s blocked by risk (%s)", sym, strat.name, reason)
                    continue
                order, position = broker.execute_decision(decision, current_price)
                risk.on_open(decision, current_price)
                logger.info("[%s] %s ORDER->%s POSITION->%s", sym, strat.name, order, position)
        except Exception as exc:
            logger.error("[%s] runner_failed error=%s", sym, exc)
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
