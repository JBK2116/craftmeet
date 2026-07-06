import logging
from typing import Any

from redis.asyncio import Redis

from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

redis: Redis | None = None


async def setup_redis():
    """
    Initialize the global Redis client from settings.

    Note:
        Keys and Values in the cache are stored as type `string`
    """
    global redis
    redis = Redis.from_url(
        url=settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )
    logger.info(
        "redis server started",
        extra={
            "url": settings.REDIS_URL,
            "max_connections": settings.REDIS_MAX_CONNECTIONS,
        },
    )


async def close_redis():
    """Close the global Redis connection. No-op if not initialized."""
    global redis
    if redis is None:
        return
    await redis.aclose()
    logger.info("redis server closed")


async def get_cache(key: str) -> Any:
    """Return the value for *key*, or ``None`` if the key is absent."""
    if redis is None:
        raise RuntimeError("redis server is not running")
    return await redis.get(key)


async def del_redis(key: str) -> int | None:
    """Delete *key*. Returns the number of keys removed (0 or 1)."""
    if redis is None:
        raise RuntimeError("redis server is not running")
    return await redis.delete(key)


async def set_redis(key: str, value: str, ttl: int) -> Any:
    """Set *key* to *value* with the given *ttl* in seconds."""
    if redis is None:
        raise RuntimeError("redis server is not running")
    return await redis.set(key, value, ttl)
