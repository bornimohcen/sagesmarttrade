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

from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger, setup_logging


def main() -> int:
    setup_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    account_id = "paper-loop"
    symbols = settings.symbols.default_universe
    strategies = settings.strategies.enabled

    logger.info(
        "paper_trade_loop_started event=loop_start account_id=%s symbols=%s strategies=%s",
        account_id,
        symbols,
        strategies,
    )

    # Heartbeat-style log for this stub loop.
    logger.info(
        "loop_iteration event=loop_iteration account_id=%s equity=%.2f open_trades=%d",
        account_id,
        settings.brokers.paper.starting_equity,
        0,
    )

    # TODO: integrate StrategyManager, RiskManager, and PaperBroker here using these settings.
    return 0


if __name__ == "__main__":
    sys.exit(main())
