#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.env import load_env_file, mask_value


REQUIRED_KEYS = [
    "BROKER_API_KEY",
    "BROKER_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
]


def main() -> int:
    secrets_path = os.environ.get("SECRETS_FILE", "config/secrets.env")
    env_values = load_env_file(secrets_path)

    print(f"verify_installation: checking secrets at {secrets_path}")

    missing = []
    for key in REQUIRED_KEYS:
        val = os.environ.get(key) or env_values.get(key)
        if not val:
            missing.append(key)
        else:
            print(f"- {key}: present (len={len(val)}) masked={mask_value(val)}")

    if missing:
        print("Missing required keys:", ", ".join(missing))
        return 1

    print("All required secrets are present (values masked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
