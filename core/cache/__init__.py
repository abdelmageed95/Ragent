"""
Caching Infrastructure for Performance Optimization

This package provides Redis-based caching for:
- Embeddings (text and image)
- Query responses
- User sessions
- RAG retrieval results

Benefits:
- 50-80% latency reduction
- Reduced API costs
- Better scalability
- Improved user experience
"""

from core.cache.redis_manager import RedisManager, get_redis_manager
from core.cache.embedding_cache import EmbeddingCache
from core.cache.query_cache import QueryCache

__all__ = [
    'RedisManager',
    'get_redis_manager',
    'EmbeddingCache',
    'QueryCache',
]
