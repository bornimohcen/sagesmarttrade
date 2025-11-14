import random
import time
from dataclasses import dataclass
from typing import Dict, Iterator, Optional


@dataclass
class Bar:
    ts: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class SimulatedMarketFetcher:
    """Generates synthetic candles to exercise the pipeline.

    This is a placeholder until real REST/WebSocket connectors are wired.
    """

    def __init__(self, symbol: str, start_price: float = 100.0, sigma: float = 0.001):
        self.symbol = symbol
        self.price = start_price
        self.sigma = sigma

    def stream(self, interval_sec: float = 1.0) -> Iterator[Dict]:
        while True:
            # Simple random walk for demo
            drift = random.gauss(0, self.sigma)
            o = self.price
            c = max(0.0001, o * (1 + drift))
            h = max(o, c) * (1 + abs(random.gauss(0, self.sigma / 2)))
            l = min(o, c) * (1 - abs(random.gauss(0, self.sigma / 2)))
            v = abs(random.gauss(1000, 200))
            self.price = c
            yield {
                "symbol": self.symbol,
                "ts": time.time(),
                "o": o,
                "h": h,
                "l": l,
                "c": c,
                "v": v,
            }
            time.sleep(interval_sec)


class HistoricalRESTFetcher:
    """Placeholder for historical REST fetching.

    Implement `fetch(symbol, start, end, interval)` to return iterator of bars.
    """

    def fetch(self, symbol: str, start: str, end: str, interval: str):
        raise NotImplementedError("Connect to provider and return historical bars")


class LiveWebSocketFetcher:
    """Placeholder for websocket live feed connector."""

    def connect(self, symbols):
        raise NotImplementedError("Connect to provider websocket and yield messages")

