#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.env import load_env_file
from sagetrade.telegram.bot import TelegramBot, TelegramBotConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SAGE SMART TRADE Telegram bot (sandbox).")
    parser.add_argument(
        "--polling-timeout",
        type=int,
        default=30,
        help="Long-polling timeout in seconds (default: 30).",
    )
    args = parser.parse_args()

    # Load secrets from config/secrets.env if present.
    load_env_file()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Set it in config/secrets.env or environment before running this script."
        )

    allowed_raw = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
    allowed_ids = []
    if allowed_raw:
        for part in allowed_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                allowed_ids.append(int(part))
            except ValueError:
                continue

    cfg = TelegramBotConfig(
        token=token,
        allowed_user_ids=allowed_ids or None,
        polling_timeout=args.polling_timeout,
    )

    bot = TelegramBot(cfg)
    print("Starting Telegram bot in sandbox mode. Press Ctrl+C to stop.")
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        print("\nTelegram bot stopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

