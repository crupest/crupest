"""Tiny per-action cooldowns for the outbound boundary."""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping


class Cooldowns:
    """At most one allowed call per key per window.

    The first call is always allowed (no warm-up wait), which matters after a
    restart: a single poke or upload should work immediately.
    """

    def __init__(self, windows: Mapping[str, float], clock: Callable[[], float] = time.monotonic) -> None:
        self._windows = {str(key): float(value) for key, value in windows.items() if value > 0}
        self._last: dict[str, float] = {}
        self._clock = clock

    def allow(self, key: str) -> bool:
        """Return True and start (or keep) the window when the call may run."""
        window = self._windows.get(key)
        if window is None:
            return True
        now = self._clock()
        last = self._last.get(key)
        if last is not None and now - last < window:
            return False
        self._last[key] = now
        return True

    def reset(self) -> None:
        self._last.clear()
