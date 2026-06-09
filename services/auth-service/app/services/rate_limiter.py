from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.core.config import settings


class RateLimiter:
    """In-memory sliding-window rate limiter keyed by email address."""

    def __init__(self) -> None:
        self._failures: dict[str, list[datetime]] = defaultdict(list)

    def _clean_window(self, email: str) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.rate_limit_window_minutes
        )
        self._failures[email] = [ts for ts in self._failures[email] if ts > cutoff]

    def is_blocked(self, email: str) -> bool:
        self._clean_window(email)
        return len(self._failures[email]) >= settings.rate_limit_attempts

    def record_failure(self, email: str) -> None:
        self._clean_window(email)
        self._failures[email].append(datetime.now(timezone.utc))

    def reset(self, email: str) -> None:
        self._failures.pop(email, None)


rate_limiter = RateLimiter()
