"""Shared rate limiter instance for slowapi.

If the REDIS_URL environment variable is set, the limiter uses Redis as
its shared storage backend for cross-worker rate limiting. Otherwise it
falls back to in-memory (single-worker only).
"""

import os

from slowapi import Limiter


def _get_ip_key(request=None) -> str:
    """Extract client IP from request or return a fallback.

    slowapi calls this both with and without a request argument depending
    on the code path (decorator vs. app.state.limiter inspection).
    """
    if request is None:
        return "unknown"
    return request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")


_storage_uri = os.environ.get("REDIS_URL", "")
limiter = Limiter(key_func=_get_ip_key, storage_uri=_storage_uri or None)
