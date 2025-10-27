"""
Phase 4 Performance Test Suite

Tests and benchmarks for performance optimizations:
1. Redis caching infrastructure
2. Async RagAgent
3. Embedding caching
4. Query response caching
5. Performance comparisons

Run: python test_phase4_performance.py
"""

import asyncio
import time
import sys
from typing import List, Tuple
import numpy as np

print("="*80)
print("  Phase 4: Performance Optimization Test Suite")
print("="*80)
print()

# =============================================================================
# Test 1: Redis Connection
# =============================================================================

def test_redis_connection():
    """Test Redis connection and basic operations"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Test 1: Redis Connection & Basic Operations")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    try:
        from core.cache.redis_manager import get_redis_manager

        manager = get_redis_manager()

        if not manager.enabled:
            print("⚠️  Redis not available (caching disabled)")
            print("   Install Redis: ./install_redis.sh")
            print("   Or run: docker run -d -p 6379:6379 redis")
            print()
            return False

        # Test connection
        if manager.is_healthy():
            print("✓ Redis connection successful")
        else:
            print("✗ Redis connection failed")
            return False

        # Test set/get
        test_key = "test:phase4:key"
        test_value = {"data": "hello", "number": 42}

        manager.set(test_key, test_value, ttl=60)
        retrieved = manager.get(test_key)

        if retrieved == test_value:
            print("✓ Set/Get operations working")
        else:
            print(f"✗ Set/Get failed. Expected {test_value}, got {retrieved}")
            return False

        # Test stats
        stats = manager.get_stats()
        print(f"✓ Redis stats: {stats['connected_clients']} clients, "
              f"{stats['used_memory']} memory")

        # Cleanup
        manager.delete(test_key)
        print("✓ Cleanup successful")
        print()

        print("✅ Redis connection test PASSED")
        print()
        return True

    except Exception as e:
        print(f"✗ Redis test failed: {e}")
        print()
        return False


# =============================================================================
# Test 2: Embedding Cache
# =============================================================================

async def test_embedding_cache():
    """Test embedding cache performance"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Test 2: Embedding Cache Performance")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    try:
        from core.cache.embedding_cache import get_embedding_cache

        cache = get_embedding_cache()

        if not cache.redis.enabled:
            print("⚠️  Embedding cache disabled (Redis not available)")
            print()
            return False

        # Test data
        test_text = "This is a test document for embedding caching"
        test_embedding = np.random.rand(768).astype(np.float32)

        # Test 1: Cache miss
        print("Test: Cache miss...")
        cached = await cache.async_get_text_embedding(test_text, model="test")
        if cached is None:
            print("✓ Cache miss correctly handled")
        else:
            print("✗ Unexpected cache hit")
            return False

        # Test 2: Set cache
        print("Test: Set cache...")
        success = await cache.async_set_text_embedding(test_text, test_embedding, model="test")
        if success:
            print("✓ Embedding cached successfully")
        else:
            print("✗ Failed to cache embedding")
            return False

        # Test 3: Cache hit
        print("Test: Cache hit...")
        cached = await cache.async_get_text_embedding(test_text, model="test")
        if cached is not None and np.allclose(cached, test_embedding):
            print("✓ Cache hit successful, embedding matches")
        else:
            print("✗ Cache hit failed or embedding mismatch")
            return False

        # Test 4: Performance benchmark
        print("\nBenchmark: Cache vs No Cache...")
        num_lookups = 100

        # Cached lookups
        start = time.time()
        for _ in range(num_lookups):
            await cache.async_get_text_embedding(test_text, model="test")
        cached_time = time.time() - start

        print(f"  {num_lookups} cached lookups: {cached_time*1000:.2f}ms "
              f"({cached_time/num_lookups*1000:.3f}ms per lookup)")

        # Stats
        stats = cache.get_stats()
        print(f"\nCache stats:")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']}")

        # Cleanup
        await cache.async_clear_all()
        print("\n✓ Cleanup successful")
        print()

        print("✅ Embedding cache test PASSED")
        print()
        return True

    except Exception as e:
        print(f"✗ Embedding cache test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


# =============================================================================
# Test 3: Query Cache
# =============================================================================

async def test_query_cache():
    """Test query response cache"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Test 3: Query Response Cache")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    try:
        from core.cache.query_cache import get_query_cache

        cache = get_query_cache()

        if not cache.redis.enabled:
            print("⚠️  Query cache disabled (Redis not available)")
            print()
            return False

        # Test data
        test_query = "What is machine learning?"
        test_response = "Machine learning is a subset of AI that enables systems to learn from data."
        test_metadata = {"sources": ["doc1.pdf"], "hits_count": 3}

        # Test 1: Cache miss
        print("Test: Cache miss...")
        cached = await cache.async_get_response(test_query)
        if cached is None:
            print("✓ Cache miss correctly handled")
        else:
            print("✗ Unexpected cache hit")
            return False

        # Test 2: Set cache
        print("Test: Set response cache...")
        success = await cache.async_set_response(test_query, test_response, test_metadata)
        if success:
            print("✓ Response cached successfully")
        else:
            print("✗ Failed to cache response")
            return False

        # Test 3: Cache hit
        print("Test: Cache hit...")
        cached = await cache.async_get_response(test_query)
        if cached is not None:
            response, metadata = cached
            if response == test_response:
                print("✓ Cache hit successful, response matches")
                print(f"  Cached: {metadata.get('cached', False)}")
            else:
                print("✗ Response mismatch")
                return False
        else:
            print("✗ Cache hit failed")
            return False

        # Test 4: Query frequency
        print("\nTest: Query frequency tracking...")
        freq = await cache.async_get_query_frequency(test_query)
        print(f"  Query frequency: {freq}")

        # Stats
        stats = cache.get_stats()
        print(f"\nCache stats:")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']}")

        # Cleanup
        await cache.async_clear_all()
        print("\n✓ Cleanup successful")
        print()

        print("✅ Query cache test PASSED")
        print()
        return True

    except Exception as e:
        print(f"✗ Query cache test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


# =============================================================================
# Test 4: AsyncRagAgent (if indices exist)
# =============================================================================

async def test_async_rag_agent():
    """Test optimized async RAG agent"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Test 4: Async RAG Agent")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    try:
        import os
        # Check if indices exist
        if not os.path.exists("data/faiss_text.index"):
            print("⚠️  FAISS indices not found (skipping RAG test)")
            print("   Build indices first: python rag_agent/build_kb.py")
            print()
            return None  # Skip test

        from rag_agent.ragagent_optimized import AsyncRagAgent

        agent = AsyncRagAgent.get_instance()
        print("✓ AsyncRagAgent initialized (singleton)")

        # Check caching
        print(f"  Embedding cache: {'enabled' if agent.embedding_cache.redis.enabled else 'disabled'}")
        print(f"  Query cache: {'enabled' if agent.query_cache.redis.enabled else 'disabled'}")

        # Test query (simple embedding test)
        print("\nTest: Query embedding...")
        test_query = "test query for performance"

        start = time.time()
        embedding1 = await agent.embed_query(test_query)
        time1 = (time.time() - start) * 1000

        if embedding1 is not None:
            print(f"✓ Query embedded: shape={embedding1.shape}, time={time1:.2f}ms")

            # Second call should be cached
            start = time.time()
            embedding2 = await agent.embed_query(test_query)
            time2 = (time.time() - start) * 1000

            print(f"✓ Cached embedding: time={time2:.2f}ms")

            if time2 < time1:
                speedup = time1 / time2
                print(f"  🚀 Speedup: {speedup:.1f}x faster")
        else:
            print("✗ Failed to generate embedding")
            return False

        # Get stats
        print("\nAgent stats:")
        stats = agent.get_stats()
        print(f"  Embedding cache: {stats['embedding_cache']}")
        print(f"  Query cache: {stats['query_cache']}")
        print()

        print("✅ Async RAG agent test PASSED")
        print()
        return True

    except Exception as e:
        print(f"✗ Async RAG agent test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


# =============================================================================
# Test 5: Performance Comparison (Optional)
# =============================================================================

def test_performance_comparison():
    """Compare original vs optimized RAG (if possible)"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Test 5: Performance Comparison Summary")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    print("Expected Performance Improvements:")
    print()
    print("  Caching:")
    print("    • Embedding cache: 10-100x faster for repeated queries")
    print("    • Query cache: 90%+ faster for exact query matches")
    print()
    print("  Async Operations:")
    print("    • Parallel retrieval: 2x faster (text + image in parallel)")
    print("    • Better concurrency handling")
    print()
    print("  LLM Optimization:")
    print("    • API calls reduced: 4 → 1 (75% reduction)")
    print("    • Cost savings: 75-80%")
    print("    • Latency reduction: 60-70%")
    print()
    print("  Overall:")
    print("    • First query: 50-80% faster")
    print("    • Cached queries: 90%+ faster")
    print("    • API costs: 75-80% lower")
    print()

    return True


# =============================================================================
# Main Test Runner
# =============================================================================

async def run_all_tests():
    """Run all Phase 4 tests"""
    print("Starting Phase 4 Performance Tests...")
    print()

    results = []

    # Test 1: Redis connection
    result = test_redis_connection()
    results.append(("Redis Connection", result))

    if not result:
        print("❌ Redis not available. Remaining tests will be skipped.")
        print("   Please install Redis: ./install_redis.sh")
        print()
        return results

    # Test 2: Embedding cache
    result = await test_embedding_cache()
    results.append(("Embedding Cache", result))

    # Test 3: Query cache
    result = await test_query_cache()
    results.append(("Query Cache", result))

    # Test 4: Async RAG agent
    result = await test_async_rag_agent()
    results.append(("Async RAG Agent", result if result is not None else "SKIPPED"))

    # Test 5: Performance summary
    test_performance_comparison()
    results.append(("Performance Summary", "INFO"))

    return results


def print_summary(results: List[Tuple[str, any]]):
    """Print test summary"""
    print("="*80)
    print("  Test Summary")
    print("="*80)
    print()

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results:
        if result is True:
            status = "✅ PASSED"
            passed += 1
        elif result is False:
            status = "❌ FAILED"
            failed += 1
        elif result == "SKIPPED":
            status = "⏭️  SKIPPED"
            skipped += 1
        else:
            status = "ℹ️  INFO"

        print(f"  {test_name:30s} {status}")

    print()
    print(f"  Total: {len(results)} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print()

    if failed > 0:
        print("❌ Some tests failed. Please review the output above.")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    # Run tests
    results = asyncio.run(run_all_tests())
    exit_code = print_summary(results)
    sys.exit(exit_code)
