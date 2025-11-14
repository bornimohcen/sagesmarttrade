import os
from typing import Dict


def load_env_file(path: str = "config/secrets.env") -> Dict[str, str]:
    """
    Minimal .env loader that does not require third-party packages.
    Lines with KEY=VALUE are parsed; comments (#) and empty lines ignored.
    Loaded values are also injected into os.environ if not already set.
    """
    values: Dict[str, str] = {}
    if not os.path.exists(path):
        return values
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f.readlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # Strip optional quotes
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            values[k] = v
            os.environ.setdefault(k, v)
    return values


def mask_value(value: str, keep: int = 2) -> str:
    if value is None:
        return "<none>"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return value[:keep] + ("*" * (len(value) - (keep * 2))) + value[-keep:]

