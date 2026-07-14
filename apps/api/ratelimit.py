from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock


WINDOW_SECONDS = 60
DEFAULT_LIMIT = 60


class _Bucket:
    def __init__(self):
        self.timestamps: deque[float] = deque()
        self.lock = Lock()

    def check(self, max_per_minute: int, now: float) -> tuple[bool, int]:
        cutoff = now - WINDOW_SECONDS
        with self.lock:
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()
            if len(self.timestamps) >= max_per_minute:
                return False, len(self.timestamps)
            self.timestamps.append(now)
            return True, len(self.timestamps)


class RateLimiter:
    def __init__(self, max_per_minute: int = DEFAULT_LIMIT):
        self.max_per_minute = max_per_minute
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)
        self._meta_lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        with self._meta_lock:
            bucket = self._buckets[key]
        return bucket.check(self.max_per_minute, time.time())

    def reset(self) -> None:
        with self._meta_lock:
            self._buckets.clear()


_limiter = RateLimiter()


def is_enabled() -> bool:
    raw = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def get_limit() -> int:
    raw = os.getenv("RATE_LIMIT_PER_MINUTE", str(DEFAULT_LIMIT)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LIMIT


def configure() -> None:
    """Re-read env and apply to the singleton (call after env changes)."""
    global _limiter
    _limiter = RateLimiter(max_per_minute=get_limit())


def configure_for(limit: int) -> None:
    """Set explicit limit (used by tests)."""
    global _limiter
    _limiter = RateLimiter(max_per_minute=limit)


def check(key: str) -> tuple[bool, int]:
    return _limiter.check(key)


def reset() -> None:
    _limiter.reset()


def error_message(current: int) -> dict:
    return {
        "detail": "rate limit exceeded",
        "limit_per_minute": _limiter.max_per_minute,
        "current_count": current,
        "retry_after_seconds": WINDOW_SECONDS,
    }
