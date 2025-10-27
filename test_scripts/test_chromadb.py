#!/usr/bin/env python3
"""
Test Script for ChromaDB Vector Store (Phase 3)

This script tests the ChromaDB integration and vector store abstraction layer.
"""

import os
import sys
import numpy as np
from pathlib import Path

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_imports():
    """Test that all required modules can be imported"""
    print_section("Testing Imports")

    all_ok = True

    # Test ChromaDB
    try:
        import chromadb
        print(f"✓ ChromaDB imported (v{chromadb.__version__})")
    except ImportError as e:
        print(f"✗ ChromaDB import failed: {e}")
        all_ok = False

    # Test vector store
    try:
        from rag_agent.vector_store import (
            VectorStore,
            ChromaVectorStore,
            FAISSVectorStore,
            create_vector_store
        )
        print("✓ Vector store module imported")
    except ImportError as e:
        print(f"✗ Vector store import failed: {e}")
        all_ok = False

    return all_ok


def test_chromadb_basic():
    """Test basic ChromaDB operations"""
    print_section("Testing ChromaDB Basic Operations")

    try:
        from rag_agent.vector_store import ChromaVectorStore

        # Create test store
        print("\n1. Creating test collection...")
        store = ChromaVectorStore(
            collection_name="test_collection",
            persist_directory="test_chroma_db",
            embedding_dimension=768
        )
        print("   ✓ Collection created")

        # Add documents
        print("\n2. Adding documents...")
        test_embeddings = np.random.rand(5, 768).astype(np.float32)
        test_metadatas = [
            {"source": f"doc_{i}.pdf", "page": i, "content": f"Test content {i}"}
            for i in range(5)
        ]

        ids = store.add_documents(test_embeddings, test_metadatas)
        print(f"   ✓ Added {len(ids)} documents")

        # Count
        print("\n3. Counting documents...")
        count = store.count()
        print(f"   ✓ Total: {count} documents")

        # Search
        print("\n4. Testing search...")
        query = np.random.rand(768).astype(np.float32)
        results = store.search(query, top_k=3)
        print(f"   ✓ Found {len(results)} results")

        for i, result in enumerate(results, 1):
            print(f"   {i}. ID: {result['id']}, Score: {result['score']:.4f}")
            print(f"      Source: {result['metadata'].get('source')}")

        # Search with filter
        print("\n5. Testing filtered search...")
        filtered_results = store.search(
            query,
            top_k=3,
            filter={"source": "doc_2.pdf"}
        )
        print(f"   ✓ Filtered results: {len(filtered_results)}")

        # Get by ID
        print("\n6. Testing get by ID...")
        if ids:
            docs = store.get([ids[0]])
            print(f"   ✓ Retrieved {len(docs)} documents")

        # Clean up
        print("\n7. Cleaning up...")
        import shutil
        shutil.rmtree("test_chroma_db")
        print("   ✓ Test data removed")

        print("\n✓ ChromaDB basic operations test passed")
        return True

    except Exception as e:
        print(f"\n✗ ChromaDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store_abstraction():
    """Test the vector store abstraction layer"""
    print_section("Testing Vector Store Abstraction")

    try:
        from rag_agent.vector_store import create_vector_store

        # Test ChromaDB creation
        print("\n1. Testing ChromaDB creation via factory...")
        store = create_vector_store(
            backend="chromadb",
            collection_name="test_abstract",
            persist_directory="test_abstract_db",
            dimension=512
        )
        print(f"   ✓ Created: {type(store).__name__}")

        # Test operations through abstraction
        print("\n2. Testing abstraction operations...")
        test_embeddings = np.random.rand(3, 512).astype(np.float32)
        test_metadatas = [{"id": i} for i in range(3)]

        ids = store.add_documents(test_embeddings, test_metadatas)
        print(f"   ✓ Added {len(ids)} documents")

        query = np.random.rand(512).astype(np.float32)
        results = store.search(query, top_k=2)
        print(f"   ✓ Search returned {len(results)} results")

        count = store.count()
        print(f"   ✓ Count: {count}")

        # Clean up
        print("\n3. Cleaning up...")
        import shutil
        shutil.rmtree("test_abstract_db")
        print("   ✓ Test data removed")

        print("\n✓ Vector store abstraction test passed")
        return True

    except Exception as e:
        print(f"\n✗ Abstraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_faiss_compatibility():
    """Test FAISS backward compatibility"""
    print_section("Testing FAISS Backward Compatibility")

    try:
        from rag_agent.vector_store import create_vector_store
        import faiss

        print("\n1. Creating FAISS store via factory...")
        store = create_vector_store(
            backend="faiss",
            collection_name="test_faiss",
            persist_directory="test_faiss_data",
            dimension=384
        )
        print(f"   ✓ Created: {type(store).__name__}")

        # Test operations
        print("\n2. Testing FAISS operations...")
        test_embeddings = np.random.rand(3, 384).astype(np.float32)
        test_metadatas = [{"id": i} for i in range(3)}

        ids = store.add_documents(test_embeddings, test_metadatas)
        print(f"   ✓ Added {len(ids)} documents")

        query = np.random.rand(384).astype(np.float32)
        results = store.search(query, top_k=2)
        print(f"   ✓ Search returned {len(results)} results")

        # Test persistence
        print("\n3. Testing persistence...")
        store.persist()
        print("   ✓ Persisted successfully")

        # Clean up
        print("\n4. Cleaning up...")
        import shutil
        shutil.rmtree("test_faiss_data")
        print("   ✓ Test data removed")

        print("\n✓ FAISS compatibility test passed")
        return True

    except Exception as e:
        print(f"\n✗ FAISS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_comparison():
    """Compare ChromaDB vs FAISS performance"""
    print_section("Performance Comparison")

    try:
        import time
        from rag_agent.vector_store import create_vector_store

        n_docs = 1000
        dimension = 768
        test_embeddings = np.random.rand(n_docs, dimension).astype(np.float32)
        test_metadatas = [{"id": i, "source": f"doc_{i}.pdf"} for i in range(n_docs)]

        # ChromaDB performance
        print("\n1. ChromaDB Performance")
        chroma_store = create_vector_store(
            backend="chromadb",
            collection_name="perf_test_chroma",
            persist_directory="perf_test_chroma_db",
            dimension=dimension
        )

        start = time.time()
        chroma_store.add_documents(test_embeddings, test_metadatas)
        chroma_add_time = time.time() - start
        print(f"   Add time: {chroma_add_time:.2f}s ({n_docs} docs)")

        query = np.random.rand(dimension).astype(np.float32)
        start = time.time()
        results = chroma_store.search(query, top_k=10)
        chroma_search_time = (time.time() - start) * 1000
        print(f"   Search time: {chroma_search_time:.2f}ms")

        # FAISS performance
        print("\n2. FAISS Performance")
        faiss_store = create_vector_store(
            backend="faiss",
            collection_name="perf_test_faiss",
            persist_directory="perf_test_faiss_data",
            dimension=dimension
        )

        start = time.time()
        faiss_store.add_documents(test_embeddings, test_metadatas)
        faiss_add_time = time.time() - start
        print(f"   Add time: {faiss_add_time:.2f}s ({n_docs} docs)")

        start = time.time()
        results = faiss_store.search(query, top_k=10)
        faiss_search_time = (time.time() - start) * 1000
        print(f"   Search time: {faiss_search_time:.2f}ms")

        # Comparison
        print("\n3. Comparison")
        print(f"   ChromaDB search: {chroma_search_time:.2f}ms")
        print(f"   FAISS search: {faiss_search_time:.2f}ms")
        if faiss_search_time < chroma_search_time:
            ratio = chroma_search_time / faiss_search_time
            print(f"   → FAISS is {ratio:.1f}x faster for search")
        else:
            ratio = faiss_search_time / chroma_search_time
            print(f"   → ChromaDB is {ratio:.1f}x faster for search")

        print("\n   Note: ChromaDB offers better persistence, metadata filtering,")
        print("         and incremental updates vs FAISS raw speed")

        # Clean up
        import shutil
        shutil.rmtree("perf_test_chroma_db", ignore_errors=True)
        shutil.rmtree("perf_test_faiss_data", ignore_errors=True)

        print("\n✓ Performance comparison complete")
        return True

    except Exception as e:
        print(f"\n✗ Performance test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "★"*70)
    print("  ChromaDB Vector Store Test Suite (Phase 3)")
    print("★"*70)

    results = {}

    # Run tests
    results['imports'] = test_imports()
    results['chromadb_basic'] = test_chromadb_basic()
    results['abstraction'] = test_vector_store_abstraction()
    results['faiss_compat'] = test_faiss_compatibility()
    results['performance'] = test_performance_comparison()

    # Summary
    print_section("Test Summary")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! ChromaDB integration working correctly.")
        print("\nBenefits achieved:")
        print("  • Automatic persistence")
        print("  • Rich metadata filtering")
        print("  • Incremental updates")
        print("  • Better management")
        print("\nNext steps:")
        print("1. Migrate from FAISS: python migrate_to_chromadb.py")
        print("2. See PHASE3_COMPLETE.md for documentation")
        return 0
    else:
        print("\n⚠  Some tests failed. Please check the errors above.")
        print("\nTo fix:")
        print("1. Install ChromaDB: ./install_chromadb.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
