import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Instrument:
    symbol: str
    asset_class: str  # e.g. "crypto", "equity", "forex"
    venue: str  # e.g. "alpaca-crypto", "alpaca-equity", "fx-broker"
    min_qty: float
    max_leverage: float


def load_universe(path: str = "config/universe.json") -> Dict[str, Instrument]:
    """Load trading universe from a JSON file.

    This keeps the engine agnostic to asset class (crypto, stocks, FX, ...).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Universe file not found: {path}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    symbols = raw.get("symbols", {})
    universe: Dict[str, Instrument] = {}
    for sym, cfg in symbols.items():
        universe[sym] = Instrument(
            symbol=sym,
            asset_class=str(cfg.get("asset_class", "unknown")),
            venue=str(cfg.get("venue", "")),
            min_qty=float(cfg.get("min_qty", 0.0)),
            max_leverage=float(cfg.get("max_leverage", 1.0)),
        )
    return universe


def get_instrument(symbol: str, path: str = "config/universe.json") -> Optional[Instrument]:
    """Convenience helper to fetch a single instrument by symbol or return None."""
    universe = load_universe(path)
    return universe.get(symbol)


