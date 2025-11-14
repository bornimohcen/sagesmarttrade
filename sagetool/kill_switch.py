import os
import time
from typing import Optional, Dict


KILL_DIR = os.path.join("runtime")
KILL_FILE = os.path.join(KILL_DIR, "kill_switch.flag")


def _ensure_dir() -> None:
    os.makedirs(KILL_DIR, exist_ok=True)


def enable(reason: str = "") -> None:
    _ensure_dir()
    payload = {
        "enabled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": reason or "manual",
    }
    with open(KILL_FILE, "w", encoding="utf-8") as f:
        f.write(f"enabled_at={payload['enabled_at']}\n")
        f.write(f"reason={payload['reason']}\n")


def disable() -> None:
    if os.path.exists(KILL_FILE):
        try:
            os.remove(KILL_FILE)
        except OSError:
            pass


def is_enabled() -> bool:
    return os.path.exists(KILL_FILE)


def status() -> Dict[str, Optional[str]]:
    if not is_enabled():
        return {"enabled": "false"}
    details: Dict[str, Optional[str]] = {"enabled": "true"}
    try:
        with open(KILL_FILE, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    details[k] = v
    except Exception:
        pass
    return details

