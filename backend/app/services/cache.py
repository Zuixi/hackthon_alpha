"""Redis cache service with graceful fallback to no-op on connection failure."""
import json
import logging
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: redis.ConnectionPool | None = None


def _get_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
        )
    return _pool


def _client() -> redis.Redis:
    return redis.Redis(connection_pool=_get_pool())


def cache_get(key: str) -> Any | None:
    try:
        raw = _client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis GET failed for %s: %s", key, e)
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    try:
        _client().setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis SET failed for %s: %s", key, e)
        return False


def cache_delete(key: str) -> bool:
    try:
        _client().delete(key)
        return True
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis DELETE failed for %s: %s", key, e)
        return False


def cache_delete_pattern(pattern: str) -> bool:
    try:
        client = _client()
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=100)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
        return True
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis DELETE pattern failed for %s: %s", pattern, e)
        return False
