from __future__ import annotations

import asyncio
import time


class AsyncStartRateLimiter:
    """Limits request start times while allowing requests to stay in flight."""

    def __init__(self, rpm: int):
        if rpm <= 0:
            raise ValueError("rpm must be positive")
        self.interval = 60.0 / rpm
        self._lock = asyncio.Lock()
        self._next_start = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._next_start - now
            if delay > 0:
                await asyncio.sleep(delay)
                now = time.monotonic()
            self._next_start = max(now, self._next_start) + self.interval
