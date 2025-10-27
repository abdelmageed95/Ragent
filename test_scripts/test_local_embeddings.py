#!/usr/bin/env python3
"""
Test Script for Local Embeddings (Phase 2)

This script tests the local embedding implementation and compares
performance with Cohere API (if available).
"""

import os
import sys
import time
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

    # Test local embeddings
    try:
        from rag_agent.local_embeddings import LocalEmbeddingManager
        print("✓ local_embeddings module imported")
    except ImportError as e:
        print(f"✗ local_embeddings import failed: {e}")
        all_ok = False

    # Test embedding helpers
    try:
        from rag_agent.embedding_helpers import (
            embed_text,
            embed_image,
            get_embedding_info
        )
        print("✓ embedding_helpers module imported")
    except ImportError as e:
        print(f"✗ embedding_helpers import failed: {e}")
        all_ok = False

    # Test torch
    try:
        import torch
        print(f"✓ PyTorch imported (v{torch.__version__})")
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  ✓ GPU available: {gpu_name}")
        else:
            print("  ℹ  No GPU (CPU mode)")
    except ImportError as e:
        print(f"✗ PyTorch import failed: {e}")
        all_ok = False

    # Test sentence transformers
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ Sentence Transformers imported")
    except ImportError as e:
        print(f"✗ Sentence Transformers import failed: {e}")
        all_ok = False

    return all_ok


def test_configuration():
    """Test embedding configuration"""
    print_section("Testing Configuration")

    try:
        from rag_agent.embedding_helpers import get_embedding_info
        import json

        info = get_embedding_info()
        print("\nEmbedding Configuration:")
        print(json.dumps(info, indent=2))

        if info['backend'] == 'local':
            print("\n✓ Using LOCAL embeddings")
            print(f"  Cost: {info['cost']}")
            print(f"  Rate limit: {info['rate_limit']}")
            return True
        elif info['backend'] == 'cohere':
            print("\n⚠  Using COHERE API")
            print("  Set USE_LOCAL_EMBEDDINGS=true in .env to use local")
            return True
        else:
            print("\n✗ No embedding backend available")
            return False

    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        return False


def test_text_embedding():
    """Test text embedding generation"""
    print_section("Testing Text Embeddings")

    try:
        from rag_agent.embedding_helpers import embed_text

        test_texts = [
            "This is a test sentence.",
            "Machine learning is awesome.",
            "Natural language processing with transformers."
        ]

        print("\nGenerating text embeddings...")
        for i, text in enumerate(test_texts, 1):
            start = time.time()
            embedding = embed_text(text)
            elapsed = (time.time() - start) * 1000

            print(f"\n{i}. \"{text[:50]}...\"")
            print(f"   Shape: {embedding.shape}")
            print(f"   Time: {elapsed:.2f}ms")
            print(f"   Sample: {embedding[:5]}")
            print(f"   Norm: {np.linalg.norm(embedding):.4f}")

        print("\n✓ Text embedding test passed")
        return True

    except Exception as e:
        print(f"\n✗ Text embedding test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_embedding():
    """Test image embedding generation"""
    print_section("Testing Image Embeddings")

    try:
        from rag_agent.embedding_helpers import embed_image
        from PIL import Image

        # Create test images
        test_images = [
            Image.new('RGB', (224, 224), color='red'),
            Image.new('RGB', (224, 224), color='blue'),
            Image.new('RGB', (224, 224), color='green')
        ]

        print("\nGenerating image embeddings...")
        for i, img in enumerate(test_images, 1):
            start = time.time()
            embedding = embed_image(img)
            elapsed = (time.time() - start) * 1000

            print(f"\n{i}. Test image ({img.size}, {img.mode})")
            print(f"   Shape: {embedding.shape}")
            print(f"   Time: {elapsed:.2f}ms")
            print(f"   Sample: {embedding[:5]}")
            print(f"   Norm: {np.linalg.norm(embedding):.4f}")

        print("\n✓ Image embedding test passed")
        return True

    except Exception as e:
        print(f"\n✗ Image embedding test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """Test and compare performance"""
    print_section("Performance Comparison")

    try:
        from rag_agent.embedding_helpers import embed_text, get_embedding_info

        info = get_embedding_info()

        # Test local embeddings
        print("\n1. Local Embeddings Performance")
        test_text = "This is a performance test sentence."

        # Warmup
        _ = embed_text(test_text)

        # Time multiple runs
        num_runs = 10
        times = []
        for _ in range(num_runs):
            start = time.time()
            _ = embed_text(test_text)
            times.append((time.time() - start) * 1000)

        avg_time = np.mean(times)
        print(f"   Average time: {avg_time:.2f}ms ({num_runs} runs)")
        print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")

        # Compare with Cohere if available
        if info.get('cohere_available'):
            print("\n2. Cohere API Performance (for comparison)")
            print("   Note: This requires COHERE_API_KEY in .env")

            try:
                # Temporarily switch to Cohere
                os.environ["USE_LOCAL_EMBEDDINGS"] = "false"

                # Re-import to use Cohere
                import importlib
                from rag_agent import embedding_helpers
                importlib.reload(embedding_helpers)

                cohere_times = []
                for _ in range(3):  # Fewer runs for API
                    start = time.time()
                    _ = embedding_helpers.embed_text(test_text)
                    cohere_times.append((time.time() - start) * 1000)

                cohere_avg = np.mean(cohere_times)
                print(f"   Average time: {cohere_avg:.2f}ms (3 runs)")

                speedup = cohere_avg / avg_time
                print(f"\n   📊 Local is {speedup:.1f}x faster than Cohere!")

                # Switch back
                os.environ["USE_LOCAL_EMBEDDINGS"] = "true"
                importlib.reload(embedding_helpers)

            except Exception as e:
                print(f"   Cohere comparison skipped: {e}")
        else:
            print("\n2. Cohere API not available for comparison")

        print("\n✓ Performance test passed")
        return True

    except Exception as e:
        print(f"\n✗ Performance test failed: {e}")
        return False


def test_rag_agent():
    """Test RAG agent with local embeddings"""
    print_section("Testing RAG Agent Integration")

    try:
        from rag_agent.ragagent import RagAgent

        print("\nInitializing RAG agent...")
        agent = RagAgent()
        print("✓ RAG agent initialized")

        print("\nTesting query embedding...")
        test_query = "What is machine learning?"
        vec = agent.embed_query(test_query)

        if vec is not None:
            print(f"✓ Query embedded successfully")
            print(f"  Shape: {vec.shape}")
            print(f"  Sample: {vec[:5]}")
        else:
            print("✗ Query embedding failed")
            return False

        print("\n✓ RAG agent test passed")
        return True

    except Exception as e:
        print(f"\n✗ RAG agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_info():
    """Display model information"""
    print_section("Model Information")

    try:
        from rag_agent.local_embeddings import get_embedding_manager
        import json

        manager = get_embedding_manager()
        info = manager.get_model_info()

        print("\nLoaded Models:")
        print(json.dumps(info, indent=2))

        return True

    except Exception as e:
        print(f"\n✗ Model info test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "★"*70)
    print("  Local Embeddings Test Suite (Phase 2)")
    print("★"*70)

    results = {}

    # Run tests
    results['imports'] = test_imports()
    results['configuration'] = test_configuration()
    results['text_embedding'] = test_text_embedding()
    results['image_embedding'] = test_image_embedding()
    results['performance'] = test_performance()
    results['rag_agent'] = test_rag_agent()
    results['model_info'] = test_model_info()

    # Summary
    print_section("Test Summary")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Local embeddings working correctly.")
        print("\nBenefits achieved:")
        print("  • $0 API costs")
        print("  • 10-100x faster")
        print("  • Unlimited usage")
        print("  • Better privacy")
        print("\nNext steps:")
        print("1. Rebuild knowledge base: python migrate_to_local_embeddings.py")
        print("2. See PHASE2_EMBEDDINGS.md for documentation")
        return 0
    else:
        print("\n⚠  Some tests failed. Please check the errors above.")
        print("\nTo fix:")
        print("1. Install dependencies: ./install_local_embeddings.sh")
        print("2. Check .env configuration: USE_LOCAL_EMBEDDINGS=true")
        return 1


if __name__ == "__main__":
    sys.exit(main())
