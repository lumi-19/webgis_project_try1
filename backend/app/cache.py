
"""
Simple in-memory caching with expiration for DisasterScope.
"""

import time
from typing import Any, Optional


class SimpleCache:
    def __init__(self, expiration_seconds: int = 300):
        self.store: dict[str, tuple[Any, float]] = {}
        self.expiration = expiration_seconds

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + (ttl if ttl is not None else self.expiration)
        self.store[key] = (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        item = self.store.get(key)
        if not item:
            return None

        value, expiry = item
        if time.time() < expiry:
            return value

        # expired
        del self.store[key]
        return None

    def clear(self) -> None:
        self.store.clear()


cache = SimpleCache(expiration_seconds=300)
