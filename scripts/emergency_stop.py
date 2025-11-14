#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.kill_switch import enable, status


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable global kill-switch (emergency stop)")
    parser.add_argument("--reason", default="manual", help="Reason to record")
    args = parser.parse_args()

    enable(args.reason)
    print("Kill-switch ENABLED.")
    print("Status:", status())
    return 0


if __name__ == "__main__":
    sys.exit(main())
