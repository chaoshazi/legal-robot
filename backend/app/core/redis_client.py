"""Async Redis client singleton with connection management."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisClient:
    """Lazy async Redis client.

    Usage:
        redis = RedisClient()
        await redis.set("key", "value", ex=300)
        val = await redis.get("key")
    """

    def __init__(self) -> None:
        self._redis: Any = None
        self._url: str = ""

    @property
    def connected(self) -> bool:
        return self._redis is not None

    async def connect(self, url: str) -> None:
        if not url:
            logger.info("Redis URL not configured — running without Redis.")
            return
        if self._redis is not None:
            return
        try:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(url, decode_responses=True)
            await self._redis.ping()
            self._url = url
            logger.info("Redis connected: %s", url)
        except Exception as e:
            self._redis = None
            logger.warning("Redis connection failed (%s) — running without Redis.", e)

    async def disconnect(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            logger.info("Redis disconnected.")

    async def get(self, key: str) -> str | None:
        if self._redis is None:
            return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning("Redis get error: %s", e)
            return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(key, value, ex=ex)
        except Exception as e:
            logger.warning("Redis set error: %s", e)

    async def delete(self, key: str) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning("Redis delete error: %s", e)

    async def exists(self, key: str) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.exists(key))
        except Exception:
            return False

    async def expire(self, key: str, seconds: int) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.expire(key, seconds)
        except Exception as e:
            logger.warning("Redis expire error: %s", e)


# Module-level singleton
_redis_client = RedisClient()


def get_redis() -> RedisClient:
    return _redis_client
