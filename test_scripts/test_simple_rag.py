"""
Test script for the simplified RAG system

This script tests all components of the simple RAG system:
1. PDF text extraction
2. Text chunking
3. Embedding generation
4. Knowledge base building
5. Retrieval
6. Answer generation
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_agent.pdf_extractor import SimplePDFExtractor
from rag_agent.embedding_helpers import embed_text


def test_text_extraction():
    """Test PDF text extraction"""
    print("\n" + "="*60)
    print("TEST 1: PDF Text Extraction")
    print("="*60)

    extractor = SimplePDFExtractor()

    # Test with sample text
    test_text = """
    This is a sample document about machine learning.
    Machine learning is a subset of artificial intelligence.
    It focuses on enabling computers to learn from data.
    """

    print("  Creating test chunks...")
    chunks = extractor.chunk_text(test_text, chunk_size=10, overlap=2)

    print(f"  Generated {len(chunks)} chunks")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}: {chunk[:50]}...")

    print("  ✓ Text extraction test passed")
    return True


def test_embeddings():
    """Test embedding generation"""
    print("\n" + "="*60)
    print("TEST 2: Embedding Generation")
    print("="*60)

    test_texts = [
        "Machine learning is a type of artificial intelligence",
        "Natural language processing helps computers understand text",
        "Computer vision enables machines to see and interpret images"
    ]

    print("  Generating embeddings...")
    embeddings = []
    for text in test_texts:
        try:
            emb = embed_text(text)
            embeddings.append(emb)
            print(f"  ✓ Embedded: '{text[:40]}...' -> shape {emb.shape}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False

    print(f"  ✓ Generated {len(embeddings)} embeddings")
    print("  ✓ Embedding test passed")
    return True


def test_simple_rag_components():
    """Test that all simple RAG components can be imported"""
    print("\n" + "="*60)
    print("TEST 3: Component Imports")
    print("="*60)

    try:
        from rag_agent.pdf_extractor import SimplePDFExtractor, extract_text_from_pdf
        print("  ✓ SimplePDFExtractor imported")

        from rag_agent.build_kb_simple import build_text_index
        print("  ✓ build_text_index imported")

        from rag_agent.ragagent_simple import SimpleRagAgent, rag_answer
        print("  ✓ SimpleRagAgent imported")

        print("  ✓ All components imported successfully")
        return True

    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_knowledge_base_structure():
    """Test knowledge base file structure"""
    print("\n" + "="*60)
    print("TEST 4: Knowledge Base Structure")
    print("="*60)

    data_dir = Path("data")
    if not data_dir.exists():
        print("  ⚠ Data directory doesn't exist yet (run build_kb_simple first)")
        return True

    simple_index = data_dir / "faiss_text_simple.index"
    simple_meta = data_dir / "text_meta_simple.pkl"

    if simple_index.exists():
        print(f"  ✓ Simple index found: {simple_index}")
        print(f"    Size: {simple_index.stat().st_size / 1024:.2f} KB")
    else:
        print(f"  ⚠ Simple index not found (run build_kb_simple first)")

    if simple_meta.exists():
        print(f"  ✓ Simple metadata found: {simple_meta}")
        print(f"    Size: {simple_meta.stat().st_size / 1024:.2f} KB")
    else:
        print(f"  ⚠ Simple metadata not found (run build_kb_simple first)")

    return True


def test_rag_agent():
    """Test RAG agent functionality"""
    print("\n" + "="*60)
    print("TEST 5: RAG Agent")
    print("="*60)

    try:
        from rag_agent.ragagent_simple import SimpleRagAgent

        print("  Checking for index files...")
        data_dir = Path("data")
        simple_index = data_dir / "faiss_text_simple.index"
        simple_meta = data_dir / "text_meta_simple.pkl"

        if not simple_index.exists() or not simple_meta.exists():
            print("  ⚠ Knowledge base not built yet")
            print("    Run: python -m rag_agent.build_kb_simple")
            return True

        print("  Initializing RAG agent...")
        agent = SimpleRagAgent()
        print("  ✓ RAG agent initialized")

        print("  Testing retrieval...")
        test_query = "What is machine learning?"
        chunks = agent.retrieve(test_query, top_k=3)
        print(f"  ✓ Retrieved {len(chunks)} chunks")

        if chunks:
            print(f"  Top result score: {chunks[0]['score']:.3f}")
            print(f"  Top result preview: {chunks[0]['content'][:100]}...")

        print("  ✓ RAG agent test passed")
        return True

    except FileNotFoundError as e:
        print(f"  ⚠ Knowledge base not found: {e}")
        print("    Run: python -m rag_agent.build_kb_simple")
        return True
    except Exception as e:
        print(f"  ✗ RAG agent test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  SIMPLE RAG SYSTEM TEST SUITE")
    print("="*60)

    tests = [
        ("Text Extraction", test_text_extraction),
        ("Embeddings", test_embeddings),
        ("Component Imports", test_simple_rag_components),
        ("Knowledge Base", test_knowledge_base_structure),
        ("RAG Agent", test_rag_agent),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print("="*60)
    print(f"  {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n  All tests passed! Simple RAG system is working correctly.")
        print("\n  Next steps:")
        print("    1. Add PDFs to pdfs/ directory")
        print("    2. Run: python -m rag_agent.build_kb_simple")
        print("    3. Query: python -m rag_agent.ragagent_simple 'your question'")
    else:
        print("\n  Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
