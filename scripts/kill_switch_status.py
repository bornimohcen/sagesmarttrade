#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetool.kill_switch import status


def main() -> int:
    print("Kill-switch status:", status())
    return 0


if __name__ == "__main__":
    sys.exit(main())
