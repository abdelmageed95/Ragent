"""
Redis Connection Manager

Provides centralized Redis connection management with:
- Connection pooling
- Automatic reconnection
- Health checks
- Graceful fallback when Redis unavailable
"""

import os
import logging
from typing import Optional, Any
import json
import pickle
import hashlib

try:
    import redis
    from redis.asyncio import Redis as AsyncRedis
    from redis.exceptions import ConnectionError, TimeoutError, RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning(
        "Redis not installed. Install with: pip install redis\n"
        "Caching will be disabled."
    )

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis connection manager with automatic fallback.

    Features:
    - Connection pooling for performance
    - Automatic health checks
    - Graceful degradation when Redis unavailable
    - Support for both sync and async operations
    - TTL (time-to-live) support
    - Key namespacing
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = False,  # False for binary data
        enabled: bool = True
    ):
        """
        Initialize Redis manager.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if auth enabled)
            max_connections: Max connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            decode_responses: Decode responses to strings
            enabled: Enable/disable caching globally
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self._client: Optional[redis.Redis] = None
        self._async_client: Optional[AsyncRedis] = None
        self._healthy = False

        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled")
            self.enabled = False
            return

        if not self.enabled:
            logger.info("Redis caching disabled by configuration")
            return

        self.host = host
        self.port = port
        self.db = db
        self.password = password

        # Create connection pool
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=decode_responses
        )

        # Create async connection pool
        self.async_pool = redis.asyncio.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=decode_responses
        )

        logger.info(f"RedisManager initialized: {host}:{port} DB={db}")

    @property
    def client(self) -> Optional[redis.Redis]:
        """Get synchronous Redis client"""
        if not self.enabled:
            return None

        if self._client is None:
            try:
                self._client = redis.Redis(connection_pool=self.pool)
                # Test connection
                self._client.ping()
                self._healthy = True
                logger.info("✓ Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._healthy = False
                self.enabled = False
                return None

        return self._client

    @property
    def async_client(self) -> Optional[AsyncRedis]:
        """Get asynchronous Redis client"""
        if not self.enabled:
            return None

        if self._async_client is None:
            try:
                self._async_client = AsyncRedis(connection_pool=self.async_pool)
                self._healthy = True
                logger.info("✓ Async Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to async Redis: {e}")
                self._healthy = False
                self.enabled = False
                return None

        return self._async_client

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        if not self.enabled:
            return False

        try:
            if self.client:
                self.client.ping()
                self._healthy = True
                return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._healthy = False

        return False

    async def async_is_healthy(self) -> bool:
        """Check if async Redis connection is healthy"""
        if not self.enabled:
            return False

        try:
            if self.async_client:
                await self.async_client.ping()
                self._healthy = True
                return True
        except Exception as e:
            logger.warning(f"Async Redis health check failed: {e}")
            self._healthy = False

        return False

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not self.enabled or not self.client:
            return default

        try:
            value = self.client.get(key)
            if value is None:
                return default

            # Try to unpickle
            try:
                return pickle.loads(value)
            except:
                # If unpickle fails, return raw value
                return value
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            return default

    async def async_get(self, key: str, default: Any = None) -> Optional[Any]:
        """Async version of get"""
        if not self.enabled or not self.async_client:
            return default

        try:
            value = await self.async_client.get(key)
            if value is None:
                return default

            try:
                return pickle.loads(value)
            except:
                return value
        except Exception as e:
            logger.warning(f"Async cache get error for key '{key}': {e}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful
        """
        if not self.enabled or not self.client:
            return False

        try:
            # Pickle the value
            pickled_value = pickle.dumps(value)

            # Set with options
            if ttl:
                result = self.client.setex(key, ttl, pickled_value)
            elif nx:
                result = self.client.setnx(key, pickled_value)
            else:
                result = self.client.set(key, pickled_value, xx=xx)

            return bool(result)
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False

    async def async_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Async version of set"""
        if not self.enabled or not self.async_client:
            return False

        try:
            pickled_value = pickle.dumps(value)

            if ttl:
                result = await self.async_client.setex(key, ttl, pickled_value)
            elif nx:
                result = await self.async_client.setnx(key, pickled_value)
            else:
                result = await self.async_client.set(key, pickled_value, xx=xx)

            return bool(result)
        except Exception as e:
            logger.warning(f"Async cache set error for key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self.enabled or not self.client:
            return 0

        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return 0

    async def async_delete(self, *keys: str) -> int:
        """Async version of delete"""
        if not self.enabled or not self.async_client:
            return 0

        try:
            return await self.async_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Async cache delete error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.enabled or not self.client:
            return False

        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists error: {e}")
            return False

    async def async_exists(self, key: str) -> bool:
        """Async version of exists"""
        if not self.enabled or not self.async_client:
            return False

        try:
            return bool(await self.async_client.exists(key))
        except Exception as e:
            logger.warning(f"Async cache exists error: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment key value"""
        if not self.enabled or not self.client:
            return None

        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache incr error: {e}")
            return None

    async def async_incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Async version of incr"""
        if not self.enabled or not self.async_client:
            return None

        try:
            return await self.async_client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Async cache incr error: {e}")
            return None

    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear pattern error: {e}")
            return 0

    async def async_clear_pattern(self, pattern: str) -> int:
        """Async version of clear_pattern"""
        if not self.enabled or not self.async_client:
            return 0

        try:
            # Note: keys() operation can be slow on large datasets
            # Consider using SCAN in production
            keys = await self.async_client.keys(pattern)
            if keys:
                return await self.async_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Async cache clear pattern error: {e}")
            return 0

    def flush_db(self) -> bool:
        """Flush entire database (use with caution!)"""
        if not self.enabled or not self.client:
            return False

        try:
            self.client.flushdb()
            logger.warning("Redis database flushed!")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled or not self.client:
            return {"enabled": False}

        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected": self._healthy,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    def _calculate_hit_rate(self, info: dict) -> str:
        """Calculate cache hit rate"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return "0%"

        rate = (hits / total) * 100
        return f"{rate:.2f}%"

    def close(self):
        """Close Redis connections"""
        try:
            if self._client:
                self._client.close()
                self._client = None
            if self._async_client:
                # Async client close needs to be awaited
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(self._async_client.close())
                    else:
                        loop.run_until_complete(self._async_client.close())
                except:
                    pass
                self._async_client = None
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    @staticmethod
    def make_key(*parts, prefix: str = "rag") -> str:
        """
        Create a namespaced cache key.

        Args:
            *parts: Key components
            prefix: Key prefix/namespace

        Returns:
            Formatted cache key
        """
        key_parts = [str(p) for p in parts if p is not None]
        return f"{prefix}:{':'.join(key_parts)}"

    @staticmethod
    def hash_key(data: str) -> str:
        """
        Create a hash from data for use as cache key.

        Args:
            data: Data to hash

        Returns:
            MD5 hash string
        """
        return hashlib.md5(data.encode('utf-8')).hexdigest()


# Global instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager(force_new: bool = False) -> RedisManager:
    """
    Get global Redis manager instance.

    Args:
        force_new: Force creation of new instance

    Returns:
        RedisManager instance
    """
    global _redis_manager

    if force_new or _redis_manager is None:
        # Read from environment
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD")
        enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"

        _redis_manager = RedisManager(
            host=host,
            port=port,
            db=db,
            password=password,
            enabled=enabled
        )

    return _redis_manager


if __name__ == "__main__":
    # Test Redis connection
    print("Testing Redis Manager...")

    manager = get_redis_manager()

    if manager.is_healthy():
        print("✓ Redis connected")

        # Test set/get
        manager.set("test:key", {"data": "hello"}, ttl=60)
        value = manager.get("test:key")
        print(f"✓ Set/Get test: {value}")

        # Test stats
        stats = manager.get_stats()
        print(f"✓ Stats: {stats}")

        # Cleanup
        manager.delete("test:key")
        print("✓ Cleanup done")
    else:
        print("✗ Redis not available - caching disabled")
        print("  Install: pip install redis")
        print("  Start Redis: docker run -d -p 6379:6379 redis")
