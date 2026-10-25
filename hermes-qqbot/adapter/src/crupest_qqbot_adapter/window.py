"""Single-conversation active window."""
from __future__ import annotations

import time
from collections.abc import Callable


class Window:
    """A timestamp that outlives one request: any successful send refreshes it."""

    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl
        self._clock = clock
        self._last: float | None = None

    def touch(self) -> None:
        self._last = self._clock()

    def active(self) -> bool:
        if self._last is None:
            return False
        return (self._clock() - self._last) < self._ttl

    def clear(self) -> None:
        self._last = None

    @property
    def ttl(self) -> float:
        return self._ttl
