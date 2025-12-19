from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request

from app.core.config import Settings


class RateLimiter:
    """
    In-memory rate limiter with simple time-bucket counters; compatible shape for Redis swap.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.counters: Dict[Tuple[str, str], Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    def check(self, request: Request, user_id: str | None) -> None:
        if not user_id:
            return
        path = request.url.path
        now = time.time()

        if path.startswith("/resume/generate"):
            self._consume(user_id, "resume_day", self.settings.resume_per_day, 86400, now)
            self._consume(user_id, "render_hour", self.settings.render_per_hour, 3600, now)
        elif path.startswith("/profile/ingest"):
            self._consume(user_id, "ingest_day", self.settings.ingest_per_day, 86400, now)
        elif path.startswith("/runs/"):
            # read-only; no limit
            return

    def _consume(self, user_id: str, key: str, limit: int, window: int, now: float) -> None:
        count, start = self.counters[(user_id, key)]
        if now - start >= window:
            count, start = 0, now
        if count >= limit:
            raise Exception(f"rate limit exceeded for {key} ({limit}/{window}s)")
        self.counters[(user_id, key)] = (count + 1, start)
