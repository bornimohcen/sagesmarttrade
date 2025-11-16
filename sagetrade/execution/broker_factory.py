from __future__ import annotations

from sagetrade.execution.alpaca_broker import AlpacaBroker
from sagetrade.execution.paper_broker import PaperBroker
from sagetrade.utils.config import get_settings


def build_broker():
    settings = get_settings()
    default = settings.brokers.default.lower()
    if default == "alpaca":
        base_url = settings.brokers.alpaca.base_url
        return AlpacaBroker(base_url=base_url)
    # fallback to paper broker
    return PaperBroker(initial_balance=settings.brokers.paper.starting_equity, account_id="paper-loop")

