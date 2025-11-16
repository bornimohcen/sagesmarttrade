from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Union

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore[assignment]


PathLike = Union[str, Path]


@dataclass
class AppSettings:
    name: str = "SAGE SmartTrade"
    env: str = "dev"
    base_currency: str = "USD"


@dataclass
class DataSettings:
    base_dir: str = "data"
    market_dir: str = "data/market"
    text_dir: str = "data/text"


@dataclass
class RiskSettings:
    max_risk_per_trade_pct: float = 0.005
    max_daily_loss_pct: float = 0.03
    max_symbol_exposure_pct: float = 0.2
    max_open_trades: int = 10


@dataclass
class AlpacaBrokerSettings:
    base_url: str = "https://paper-api.alpaca.markets"
    key_env: str = "ALPACA_API_KEY"
    secret_env: str = "ALPACA_API_SECRET"


@dataclass
class BrokersSettings:
    default: str = "paper"
    alpaca: AlpacaBrokerSettings = AlpacaBrokerSettings()


@dataclass
class Settings:
    app: AppSettings = AppSettings()
    data: DataSettings = DataSettings()
    risk: RiskSettings = RiskSettings()
    brokers: BrokersSettings = BrokersSettings()


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise ImportError(
            "PyYAML is required to load settings.yaml. "
            "Install it with `pip install pyyaml`."
        )
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)  # type: ignore[no-any-return, attr-defined]
    if not isinstance(data, dict):
        return {}
    return data


def _build_dataclass(cls, data: Dict[str, Any]):
    """Merge explicit data over dataclass defaults."""
    base = asdict(cls())
    base.update(data or {})
    return cls(**base)


def load_settings(path: PathLike = "config/settings.yaml") -> Settings:
    """Load typed application settings from a YAML file.

    The schema is intentionally minimal for now and can be extended as the
    project grows (more brokers, modules, and toggles).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Settings file not found: {p}")

    raw = _load_yaml(p)

    app = _build_dataclass(AppSettings, raw.get("app", {}) or {})
    data_cfg = _build_dataclass(DataSettings, raw.get("data", {}) or {})
    risk = _build_dataclass(RiskSettings, raw.get("risk", {}) or {})

    brokers_raw = raw.get("brokers", {}) or {}
    alpaca_cfg = brokers_raw.get("alpaca", {}) or {}
    alpaca = _build_dataclass(AlpacaBrokerSettings, alpaca_cfg)
    brokers = BrokersSettings(
        default=str(brokers_raw.get("default", "paper")),
        alpaca=alpaca,
    )

    return Settings(app=app, data=data_cfg, risk=risk, brokers=brokers)


__all__ = [
    "AppSettings",
    "DataSettings",
    "RiskSettings",
    "AlpacaBrokerSettings",
    "BrokersSettings",
    "Settings",
    "load_settings",
]

