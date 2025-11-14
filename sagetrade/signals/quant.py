from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence


NumberSeq = Sequence[float]


def _rolling(values: NumberSeq, window: int) -> List[float]:
    out: List[float] = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= window:
            s -= values[i - window]
        if i + 1 < window:
            out.append(float("nan"))
        else:
            out.append(s / window)
    return out


def sma(values: NumberSeq, window: int) -> float:
    if window <= 0 or len(values) < window:
        return float("nan")
    return sum(values[-window:]) / float(window)


def ema(values: NumberSeq, window: int) -> float:
    if window <= 0 or not values:
        return float("nan")
    alpha = 2.0 / (window + 1.0)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = alpha * v + (1 - alpha) * ema_val
    return ema_val


def rsi(closes: NumberSeq, window: int = 14) -> float:
    if window <= 0 or len(closes) <= window:
        return float("nan")
    gains = []
    losses = []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        if ch > 0:
            gains.append(ch)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-ch)
    avg_gain = sma(gains, window)
    avg_loss = sma(losses, window)
    if avg_loss == 0 or avg_loss != avg_loss:  # NaN check
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def true_ranges(highs: NumberSeq, lows: NumberSeq, closes: NumberSeq) -> List[float]:
    trs: List[float] = []
    for i in range(len(highs)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        trs.append(tr)
    return trs


def atr(highs: NumberSeq, lows: NumberSeq, closes: NumberSeq, window: int = 14) -> float:
    trs = true_ranges(highs, lows, closes)
    return sma(trs, window)


def volatility(closes: NumberSeq, window: int = 20) -> float:
    if window <= 1 or len(closes) < window:
        return float("nan")
    import math

    window_vals = closes[-window:]
    mean = sum(window_vals) / float(window)
    var = sum((x - mean) ** 2 for x in window_vals) / float(window - 1)
    return math.sqrt(max(var, 0.0))


def classify_regime(vol: float, low_thresh: float = 0.005, high_thresh: float = 0.02) -> str:
    """Simple regime classifier based on volatility."""
    if vol != vol:  # NaN
        return "unknown"
    if vol < low_thresh:
        return "low_vol"
    if vol > high_thresh:
        return "high_vol"
    return "normal"


@dataclass
class QuantSignals:
    symbol: str
    window: int
    sma: float
    ema: float
    rsi: float
    atr: float
    volatility: float
    regime: str

    def as_dict(self) -> Dict[str, float]:
        return {
            "sma": self.sma,
            "ema": self.ema,
            "rsi": self.rsi,
            "atr": self.atr,
            "volatility": self.volatility,
        }


def get_signals_from_bars(symbol: str, bars: Iterable[Dict[str, float]], window: int = 20) -> QuantSignals:
    closes: List[float] = []
    highs: List[float] = []
    lows: List[float] = []
    for bar in bars:
        closes.append(float(bar["c"]))
        highs.append(float(bar.get("h", bar["c"])))
        lows.append(float(bar.get("l", bar["c"])))

    if not closes:
        return QuantSignals(
            symbol=symbol,
            window=window,
            sma=float("nan"),
            ema=float("nan"),
            rsi=float("nan"),
            atr=float("nan"),
            volatility=float("nan"),
            regime="unknown",
        )

    s = sma(closes, window)
    e = ema(closes, window)
    r = rsi(closes, min(14, max(2, window // 2)))
    a = atr(highs, lows, closes, min(14, max(2, window // 2)))
    vol = volatility(closes, window)
    regime = classify_regime(vol)

    return QuantSignals(
        symbol=symbol,
        window=window,
        sma=s,
        ema=e,
        rsi=r,
        atr=a,
        volatility=vol,
        regime=regime,
    )
