"""
R5 Operational Intelligence Platform - High-Performance In-Memory TTL Cache
Thread-safe cache with TTL expiration, bounded capacity, hit/miss telemetry,
and pattern-based invalidation for configuration, taxonomy, and high-read operational lookups.
"""

import time
import functools
import threading
from typing import Any, Dict, Optional, Callable


class CacheEntry:
    __slots__ = ("value", "expires_at", "created_at")

    def __init__(self, value: Any, ttl_seconds: float):
        self.value = value
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at


class TTLCache:
    def __init__(self, max_size: int = 1000, default_ttl_seconds: float = 300.0):
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Telemetry metrics
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            now = time.time()
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired(now):
                del self._store[key]
                self._evictions += 1
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        with self._lock:
            now = time.time()
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

            # Evict oldest entry if capacity reached
            if len(self._store) >= self.max_size and key not in self._store:
                # Find expired or oldest entry
                oldest_k = None
                oldest_time = float("inf")
                for k, v in self._store.items():
                    if v.is_expired(now):
                        oldest_k = k
                        break
                    if v.created_at < oldest_time:
                        oldest_time = v.created_at
                        oldest_k = k
                if oldest_k:
                    del self._store[oldest_k]
                    self._evictions += 1

            self._store[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys starting with given prefix."""
        with self._lock:
            keys_to_del = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in keys_to_del:
                del self._store[k]
            return len(keys_to_del)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_lookups = self._hits + self._misses
            hit_ratio = round((self._hits / total_lookups) * 100.0, 2) if total_lookups > 0 else 0.0
            now = time.time()
            active_keys = sum(1 for entry in self._store.values() if not entry.is_expired(now))

            return {
                "activeEntries": active_keys,
                "totalEntries": len(self._store),
                "maxSize": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hitRatioPct": hit_ratio
            }


# Global application cache singletons
app_cache = TTLCache(max_size=2000, default_ttl_seconds=300.0)
hierarchy_cache = TTLCache(max_size=500, default_ttl_seconds=600.0)


def cached(cache: TTLCache, prefix: str, ttl_seconds: Optional[float] = None):
    """Decorator to cache pure functions or lookups."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{prefix}:{str(args)}:{str(kwargs)}"
            val = cache.get(key)
            if val is not None:
                return val
            res = func(*args, **kwargs)
            cache.set(key, res, ttl_seconds=ttl_seconds)
            return res
        return wrapper
    return decorator
