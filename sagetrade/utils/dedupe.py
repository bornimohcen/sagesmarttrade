import time
from typing import Dict


class TTLSet:
    """A simple TTL-based deduplicator for message IDs."""

    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl = ttl_seconds
        self._store: Dict[str, float] = {}

    def add(self, key: str) -> None:
        now = time.time()
        self._store[key] = now + self.ttl
        self._sweep(now)

    def seen(self, key: str) -> bool:
        now = time.time()
        exp = self._store.get(key)
        if not exp:
            return False
        if exp < now:
            del self._store[key]
            return False
        return True

    def _sweep(self, now: float) -> None:
        expired = [k for k, exp in self._store.items() if exp < now]
        for k in expired:
            del self._store[k]

