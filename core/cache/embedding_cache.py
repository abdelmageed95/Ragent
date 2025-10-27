"""
Embedding Cache Module

Provides caching for text and image embeddings to reduce computation time.

Benefits:
- 10-100x faster for repeated queries
- Reduced GPU/CPU usage
- Lower memory pressure
- Better scalability
"""

import logging
from typing import Optional, Union, List
import numpy as np
import hashlib

from core.cache.redis_manager import RedisManager, get_redis_manager

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Cache for embeddings (text and image).

    Features:
    - Automatic key generation from content
    - TTL support for cache expiration
    - Hit/miss tracking
    - Batch caching support
    - Separate namespaces for text/image
    """

    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        ttl: int = 86400,  # 24 hours
        prefix: str = "emb"
    ):
        """
        Initialize embedding cache.

        Args:
            redis_manager: Redis manager instance
            ttl: Time-to-live in seconds (default 24h)
            prefix: Cache key prefix
        """
        self.redis = redis_manager or get_redis_manager()
        self.ttl = ttl
        self.prefix = prefix

        # Statistics
        self._hits = 0
        self._misses = 0

        logger.info(f"EmbeddingCache initialized (TTL={ttl}s)")

    def _make_key(self, content: str, model: str, namespace: str = "text") -> str:
        """
        Create cache key from content and model.

        Args:
            content: Text or image path
            model: Model name
            namespace: 'text' or 'image'

        Returns:
            Cache key
        """
        # Hash the content for shorter keys
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        return RedisManager.make_key(
            namespace, model, content_hash,
            prefix=self.prefix
        )

    def get_text_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> Optional[np.ndarray]:
        """
        Get cached text embedding.

        Args:
            text: Text to embed
            model: Model name

        Returns:
            Cached embedding or None
        """
        if not self.redis.enabled:
            return None

        key = self._make_key(text, model, "text")
        cached = self.redis.get(key)

        if cached is not None:
            self._hits += 1
            logger.debug(f"Cache HIT for text embedding (key={key[:20]}...)")
            return np.array(cached, dtype=np.float32)

        self._misses += 1
        logger.debug(f"Cache MISS for text embedding (key={key[:20]}...)")
        return None

    async def async_get_text_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> Optional[np.ndarray]:
        """Async version of get_text_embedding"""
        if not self.redis.enabled:
            return None

        key = self._make_key(text, model, "text")
        cached = await self.redis.async_get(key)

        if cached is not None:
            self._hits += 1
            logger.debug(f"Cache HIT for text embedding (key={key[:20]}...)")
            return np.array(cached, dtype=np.float32)

        self._misses += 1
        logger.debug(f"Cache MISS for text embedding (key={key[:20]}...)")
        return None

    def set_text_embedding(
        self,
        text: str,
        embedding: np.ndarray,
        model: str = "default"
    ) -> bool:
        """
        Cache text embedding.

        Args:
            text: Text that was embedded
            embedding: Embedding vector
            model: Model name

        Returns:
            True if cached successfully
        """
        if not self.redis.enabled:
            return False

        key = self._make_key(text, model, "text")

        # Convert numpy array to list for caching
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        success = self.redis.set(key, embedding_list, ttl=self.ttl)

        if success:
            logger.debug(f"Cached text embedding (key={key[:20]}...)")

        return success

    async def async_set_text_embedding(
        self,
        text: str,
        embedding: np.ndarray,
        model: str = "default"
    ) -> bool:
        """Async version of set_text_embedding"""
        if not self.redis.enabled:
            return False

        key = self._make_key(text, model, "text")
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        success = await self.redis.async_set(key, embedding_list, ttl=self.ttl)

        if success:
            logger.debug(f"Cached text embedding (key={key[:20]}...)")

        return success

    def get_image_embedding(
        self,
        image_path: str,
        model: str = "default"
    ) -> Optional[np.ndarray]:
        """
        Get cached image embedding.

        Args:
            image_path: Path to image
            model: Model name

        Returns:
            Cached embedding or None
        """
        if not self.redis.enabled:
            return None

        key = self._make_key(image_path, model, "image")
        cached = self.redis.get(key)

        if cached is not None:
            self._hits += 1
            logger.debug(f"Cache HIT for image embedding (key={key[:20]}...)")
            return np.array(cached, dtype=np.float32)

        self._misses += 1
        logger.debug(f"Cache MISS for image embedding (key={key[:20]}...)")
        return None

    async def async_get_image_embedding(
        self,
        image_path: str,
        model: str = "default"
    ) -> Optional[np.ndarray]:
        """Async version of get_image_embedding"""
        if not self.redis.enabled:
            return None

        key = self._make_key(image_path, model, "image")
        cached = await self.redis.async_get(key)

        if cached is not None:
            self._hits += 1
            logger.debug(f"Cache HIT for image embedding (key={key[:20]}...)")
            return np.array(cached, dtype=np.float32)

        self._misses += 1
        logger.debug(f"Cache MISS for image embedding (key={key[:20]}...)")
        return None

    def set_image_embedding(
        self,
        image_path: str,
        embedding: np.ndarray,
        model: str = "default"
    ) -> bool:
        """
        Cache image embedding.

        Args:
            image_path: Path to image
            embedding: Embedding vector
            model: Model name

        Returns:
            True if cached successfully
        """
        if not self.redis.enabled:
            return False

        key = self._make_key(image_path, model, "image")
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        success = self.redis.set(key, embedding_list, ttl=self.ttl)

        if success:
            logger.debug(f"Cached image embedding (key={key[:20]}...)")

        return success

    async def async_set_image_embedding(
        self,
        image_path: str,
        embedding: np.ndarray,
        model: str = "default"
    ) -> bool:
        """Async version of set_image_embedding"""
        if not self.redis.enabled:
            return False

        key = self._make_key(image_path, model, "image")
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        success = await self.redis.async_set(key, embedding_list, ttl=self.ttl)

        if success:
            logger.debug(f"Cached image embedding (key={key[:20]}...)")

        return success

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, and hit rate
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "enabled": self.redis.enabled,
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%"
        }

    def clear_text_embeddings(self, model: str = "*") -> int:
        """
        Clear text embeddings from cache.

        Args:
            model: Model name or "*" for all models

        Returns:
            Number of keys deleted
        """
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("text", model, "*", prefix=self.prefix)
        count = self.redis.clear_pattern(pattern)
        logger.info(f"Cleared {count} text embeddings for model={model}")
        return count

    async def async_clear_text_embeddings(self, model: str = "*") -> int:
        """Async version of clear_text_embeddings"""
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("text", model, "*", prefix=self.prefix)
        count = await self.redis.async_clear_pattern(pattern)
        logger.info(f"Cleared {count} text embeddings for model={model}")
        return count

    def clear_image_embeddings(self, model: str = "*") -> int:
        """
        Clear image embeddings from cache.

        Args:
            model: Model name or "*" for all models

        Returns:
            Number of keys deleted
        """
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("image", model, "*", prefix=self.prefix)
        count = self.redis.clear_pattern(pattern)
        logger.info(f"Cleared {count} image embeddings for model={model}")
        return count

    async def async_clear_image_embeddings(self, model: str = "*") -> int:
        """Async version of clear_image_embeddings"""
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("image", model, "*", prefix=self.prefix)
        count = await self.redis.async_clear_pattern(pattern)
        logger.info(f"Cleared {count} image embeddings for model={model}")
        return count

    def clear_all(self) -> int:
        """Clear all embeddings from cache"""
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("*", prefix=self.prefix)
        count = self.redis.clear_pattern(pattern)
        logger.info(f"Cleared {count} total embeddings")

        # Reset stats
        self._hits = 0
        self._misses = 0

        return count

    async def async_clear_all(self) -> int:
        """Async version of clear_all"""
        if not self.redis.enabled:
            return 0

        pattern = RedisManager.make_key("*", prefix=self.prefix)
        count = await self.redis.async_clear_pattern(pattern)
        logger.info(f"Cleared {count} total embeddings")

        # Reset stats
        self._hits = 0
        self._misses = 0

        return count


# Global instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache(force_new: bool = False) -> EmbeddingCache:
    """
    Get global embedding cache instance.

    Args:
        force_new: Force creation of new instance

    Returns:
        EmbeddingCache instance
    """
    global _embedding_cache

    if force_new or _embedding_cache is None:
        _embedding_cache = EmbeddingCache()

    return _embedding_cache


if __name__ == "__main__":
    # Test embedding cache
    print("Testing Embedding Cache...")

    cache = get_embedding_cache()

    if cache.redis.enabled:
        # Test text embedding
        test_text = "This is a test document"
        test_embedding = np.random.rand(768).astype(np.float32)

        # Cache it
        cache.set_text_embedding(test_text, test_embedding, model="test")

        # Retrieve it
        cached = cache.get_text_embedding(test_text, model="test")

        if cached is not None:
            print(f"✓ Text embedding cached and retrieved")
            print(f"  Shape: {cached.shape}")
            print(f"  Match: {np.allclose(test_embedding, cached)}")
        else:
            print("✗ Failed to retrieve cached embedding")

        # Stats
        stats = cache.get_stats()
        print(f"✓ Stats: {stats}")

        # Cleanup
        cache.clear_all()
        print("✓ Cache cleared")
    else:
        print("✗ Redis not available - caching disabled")
