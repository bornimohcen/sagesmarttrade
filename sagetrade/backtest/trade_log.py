from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class BacktestTradeRecord:
    trade_id: str
    symbol: str
    strategy_name: str
    side: str  # "long" or "short"
    qty: float
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    realized_pnl: float
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0


class TradeLog:
    def __init__(self) -> None:
        self.trades: List[BacktestTradeRecord] = []

    def add_trade(self, record: BacktestTradeRecord) -> None:
        self.trades.append(record)

    def to_csv(self, path: str | Path) -> None:
        p = Path(path)
        if not self.trades:
            return
        fieldnames = list(asdict(self.trades[0]).keys())
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in self.trades:
                writer.writerow(asdict(t))


__all__ = ["BacktestTradeRecord", "TradeLog"]

