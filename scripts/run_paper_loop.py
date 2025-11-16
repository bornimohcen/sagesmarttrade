#!/usr/bin/env python3
"""
Lightweight entry script for a future paper-trading loop.

For now it only wires up logging and configuration and prints a startup
message. The actual trading logic lives in more advanced scripts like
`scripts/paper_trade_loop.py` and can be integrated here later.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.utils.config import load_settings
from sagetrade.utils.logging import setup_logging


def main() -> int:
    setup_logging()
    settings = load_settings()
    print(
        f"Starting SAGE SmartTrade paper loop "
        f"(env={settings.app.env}, base_currency={settings.app.base_currency}, "
        f"default_broker={settings.brokers.default})"
    )
    # TODO: integrate StrategyManager, RiskManager, and PaperBroker here.
    return 0


if __name__ == "__main__":
    sys.exit(main())

