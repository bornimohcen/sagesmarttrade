from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field


PathLike = Union[str, Path]


class AppSettings(BaseModel):
    name: str = "SAGE SmartTrade"
    env: str = "dev"
    base_currency: str = "USD"
    timezone: str = "Africa/Algiers"


class DataSettings(BaseModel):
    base_dir: str = "data"
    market_dir: str = "data/market"
    text_dir: str = "data/text"
    logs_dir: str = "logs"


class RiskSettings(BaseModel):
    # Stored as fractions of equity (e.g. 0.005 = 0.5%).
    max_risk_per_trade_pct: float = Field(0.005, ge=0.0, le=0.05)
    max_daily_loss_pct: float = Field(0.03, ge=0.0, le=0.2)
    max_symbol_exposure_pct: float = Field(0.2, ge=0.0, le=1.0)
    max_open_trades: int = Field(10, ge=1, le=1000)


class PaperBrokerSettings(BaseModel):
    starting_equity: float = 10_000.0


class AlpacaBrokerSettings(BaseModel):
    base_url: str = "https://paper-api.alpaca.markets/v2"
    key_env: str = "ALPACA_API_KEY"
    secret_env: str = "ALPACA_API_SECRET"

    @property
    def key(self) -> Optional[str]:
        return os.getenv(self.key_env)

    @property
    def secret(self) -> Optional[str]:
        return os.getenv(self.secret_env)


class BrokersSettings(BaseModel):
    default: str = "paper"
    paper: PaperBrokerSettings = PaperBrokerSettings()
    alpaca: AlpacaBrokerSettings = AlpacaBrokerSettings()


class StrategiesSettings(BaseModel):
    enabled: List[str] = ["news_quick_trade"]
    per_symbol: Dict[str, List[str]] = {}


class SymbolsSettings(BaseModel):
    default_universe: List[str] = ["BTCUSD", "AAPL", "EURUSD"]


class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"

    @property
    def bot_token(self) -> Optional[str]:
        return os.getenv(self.bot_token_env)

    @property
    def chat_id(self) -> Optional[str]:
        return os.getenv(self.chat_id_env)


class AISettings(BaseModel):
    enabled: bool = False
    provider: str = "mock"  # mock | openai | local
    model: str = "gpt-4.1"
    max_output_tokens: int = 400
    language: str = "mix"  # en | ar | mix
    api_key_env: str = "OPENAI_API_KEY"


class Settings(BaseModel):
    app: AppSettings
    data: DataSettings
    risk: RiskSettings
    brokers: BrokersSettings
    strategies: StrategiesSettings = StrategiesSettings()
    symbols: SymbolsSettings = SymbolsSettings()
    telegram: TelegramSettings = TelegramSettings()
    ai: AISettings = AISettings()


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_settings_path(path: PathLike | None = None) -> Path:
    """Determine which settings file to load.

    If a path is explicitly provided, use it.
    Otherwise, try APP_ENV-specific file (settings.<env>.yaml) and
    fall back to config/settings.yaml.
    """
    if path is not None:
        return Path(path)
    base = Path("config")
    env = os.getenv("APP_ENV")
    if env:
        candidate = base / f"settings.{env}.yaml"
        if candidate.exists():
            return candidate
    return base / "settings.yaml"


@lru_cache
def get_settings(path: PathLike | None = None) -> Settings:
    cfg_path = _resolve_settings_path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    raw = _load_yaml(cfg_path)
    return Settings(**raw)


# Backwards-compat alias for earlier phases.
load_settings = get_settings


__all__ = [
    "AppSettings",
    "DataSettings",
    "RiskSettings",
    "PaperBrokerSettings",
    "AlpacaBrokerSettings",
    "BrokersSettings",
    "StrategiesSettings",
    "SymbolsSettings",
    "TelegramSettings",
    "AISettings",
    "Settings",
    "get_settings",
    "load_settings",
]
