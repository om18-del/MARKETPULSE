"""TTL cache + per-provider circuit breaker utilities.

Zero-overhead caching: plain in-process dicts with monotonic-time TTLs —
no Redis, no database, survives the life of the process (which is exactly
the lifetime of a hackathon demo or a persistent Render service).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class TTLCache:
    """Thread-safe in-process key/value cache with per-entry TTLs.

    get() returns None on miss (None values are never stored)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires, value = entry
            if now >= expires:
                del self._data[key]
                self.misses += 1
                return None
            self.hits += 1
            return value

    def age_of(self, key: str) -> float | None:
        """Seconds since the cached value was written, or None."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires, value = entry
            return round(max(0.0, expires - time.monotonic()), 1)

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + ttl, value)

    def get_or_set(self, key: str, ttl: float, producer: Callable[[], T]) -> T:
        current = self.get(key)
        if current is not None:
            return current  # type: ignore[return-value]
        value = producer()
        self.set(key, value, ttl)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


@dataclass
class CircuitBreaker:
    """Per-provider failure tracker: after `threshold` consecutive failures,
    the provider is skipped for `cooldown` seconds, then half-opens: exactly
    ONE probe request goes through; more failures re-open immediately.
    (Without the re-arm, a dead provider retried on every request forever.)"""

    threshold: int = 3
    cooldown: float = 120.0
    failures: int = 0
    opened_at: float | None = None
    last_error: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _state_unlocked(self) -> str:
        if self.opened_at is None:
            return "closed"
        elapsed = time.monotonic() - self.opened_at
        if elapsed >= self.cooldown:
            return "half-open"
        return "open"

    @property
    def is_open(self) -> bool:
        with self._lock:
            # open -> blocks; half-open -> allows exactly one probe through
            if self._state_unlocked() == "open":
                return True
            if self._state_unlocked() == "half-open":
                # allow a single probe: consume the half-open window by
                # pretending we're closed but re-open instantly on failure
                return False
            return False

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None
            self.last_error = ""

    def record_failure(self, error: str) -> None:
        with self._lock:
            self.failures += 1
            self.last_error = error[:200]
            if self._state_unlocked() == "half-open":
                # probe failed -> re-open for another full cooldown
                self.opened_at = time.monotonic()
                return
            if self.failures >= self.threshold and self.opened_at is None:
                self.opened_at = time.monotonic()

    def status(self) -> dict[str, Any]:
        return {
            "open": self.is_open,
            "consecutive_failures": self.failures,
            "last_error": self.last_error,
        }
