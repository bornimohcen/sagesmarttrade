#!/usr/bin/env python3
import argparse
import os
import sys
import socket
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.env import load_env_file
from sagetool.kill_switch import is_enabled as kill_enabled


def check_network_reachable(base_url: str, timeout: float = 3.0) -> bool:
    if not base_url:
        return False
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Startup health check")
    parser.add_argument("--secrets", default="config/secrets.env", help="Path to secrets env file")
    parser.add_argument("--check-network", action="store_true", help="Attempt simple TCP reachability to BROKER_BASE_URL")
    args = parser.parse_args()

    load_env_file(args.secrets)

    if kill_enabled():
        print("FAIL: kill-switch is ENABLED. Refusing to start.")
        return 2

    required = {
        "BROKER_API_KEY": os.environ.get("BROKER_API_KEY"),
        "BROKER_API_SECRET": os.environ.get("BROKER_API_SECRET"),
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print("FAIL: missing required env keys:", ", ".join(missing))
        return 3

    status = (os.environ.get("ACCOUNT_STATUS") or "").strip().upper()
    if status != "ACTIVE":
        print(f"FAIL: ACCOUNT_STATUS is '{status or 'unset'}' (expected ACTIVE)")
        return 4

    if args.check_network:
        base_url = os.environ.get("BROKER_BASE_URL", "")
        if not check_network_reachable(base_url):
            print(f"FAIL: cannot reach {base_url} (TCP check)")
            return 5

    print("OK: startup_check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
