from __future__ import annotations

from sagetrade.execution.alpaca_broker import AlpacaBroker
from sagetrade.execution.paper_broker import PaperBroker
from sagetrade.utils.config import get_settings


def build_broker():
    settings = get_settings()
    default = settings.brokers.default.lower()
    if default == "alpaca":
        alpaca_cfg = settings.brokers.alpaca
        return AlpacaBroker(
            base_url=alpaca_cfg.base_url,
            api_key=alpaca_cfg.resolve_key(),
            api_secret=alpaca_cfg.resolve_secret(),
        )
    # fallback to paper broker
    return PaperBroker(initial_balance=settings.brokers.paper.starting_equity, account_id="paper-loop")
