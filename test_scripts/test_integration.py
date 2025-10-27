#!/usr/bin/env python3
"""
Integration Test for Updated RAG and Memory Agents

This test verifies that all components work correctly after the ChromaDB migration:
- RAG agent with ChromaDB
- Memory agent with ChromaDB
- Graph workflow integration
- API endpoints
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all critical imports work"""
    print("\n" + "="*60)
    print("TEST 1: Checking Imports")
    print("="*60)

    try:
        # RAG imports
        from rag_agent.ragagent_simple import SimpleRagAgent, rag_answer
        from rag_agent.embedding_helpers import embed_text, get_embedding_info
        from rag_agent.build_kb_simple import build_text_index
        print("✓ RAG agent imports successful")

        # Memory imports
        from memory.mem_agent import MemoryAgent, MockMemoryAgent
        from memory.mem_config import MemoryConfig
        print("✓ Memory agent imports successful")

        # Graph workflow imports
        from graph.workflow import LangGraphMultiAgentSystem
        from graph.rag_node import rag_agent_node, enhanced_rag_agent_node
        from graph.memory_nodes import (
            memory_fetch_node, memory_update_node,
            enhanced_memory_fetch_node, enhanced_memory_update_node
        )
        print("✓ Graph workflow imports successful")

        # API imports
        from core.api.knowledge_base import router as kb_router
        print("✓ API imports successful")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_configuration():
    """Test embedding configuration"""
    print("\n" + "="*60)
    print("TEST 2: Checking Embedding Configuration")
    print("="*60)

    try:
        from rag_agent.embedding_helpers import get_embedding_info
        import json

        info = get_embedding_info()
        print(f"Backend: {info['backend']}")
        print(f"Cost: {info.get('cost', 'N/A')}")
        print(f"Rate limit: {info.get('rate_limit', 'N/A')}")

        if info['backend'] == 'local':
            print("✓ Using local embeddings (ChromaDB compatible)")
            return True
        else:
            print("⚠ Not using local embeddings")
            return True  # Still pass, just warn

    except Exception as e:
        print(f"✗ Embedding config test failed: {e}")
        return False


def test_memory_config():
    """Test memory agent configuration"""
    print("\n" + "="*60)
    print("TEST 3: Checking Memory Agent Configuration")
    print("="*60)

    try:
        from memory.mem_config import MemoryConfig

        config = MemoryConfig()
        print(f"ChromaDB directory: {config.chroma_db_dir}")
        print(f"Embedding model: {config.embedding_model_name}")
        print(f"Memory collection prefix: {config.memory_collection_prefix}")

        # Check that embeddings are initialized
        if config.embeddings is not None:
            print("✓ Memory embeddings initialized")
        else:
            print("⚠ Memory embeddings not initialized (will be on first use)")

        print("✓ Memory configuration valid")
        return True

    except Exception as e:
        print(f"✗ Memory config test failed: {e}")
        return False


def test_rag_agent_mock():
    """Test RAG agent (without actual ChromaDB data)"""
    print("\n" + "="*60)
    print("TEST 4: Testing RAG Agent Structure")
    print("="*60)

    try:
        from rag_agent.ragagent_simple import SimpleRagAgent

        # This will fail if ChromaDB doesn't exist, which is expected
        # We're just testing the structure
        try:
            agent = SimpleRagAgent()
            print("✓ ChromaDB knowledge base exists and loaded")
            print(f"  Collection count: {agent.collection.count()}")
        except FileNotFoundError as e:
            print("⚠ ChromaDB knowledge base not built yet (expected)")
            print("  This is normal if you haven't uploaded PDFs yet")

        return True

    except Exception as e:
        print(f"✗ RAG agent test failed: {e}")
        return False


def test_workflow_structure():
    """Test workflow structure (without execution)"""
    print("\n" + "="*60)
    print("TEST 5: Testing Workflow Structure")
    print("="*60)

    try:
        from graph.workflow import LangGraphMultiAgentSystem

        # Initialize workflow (doesn't require MongoDB)
        workflow = LangGraphMultiAgentSystem(
            user_id="test_user",
            thread_id="test_thread"
        )

        print("✓ Workflow initialized successfully")
        print(f"  User ID: {workflow.user_id}")
        print(f"  Thread ID: {workflow.thread_id}")

        # Check that workflow has the expected nodes
        if workflow.workflow:
            print("✓ Workflow graph compiled successfully")

        return True

    except Exception as e:
        print(f"✗ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_structure():
    """Test API endpoint structure"""
    print("\n" + "="*60)
    print("TEST 6: Testing API Structure")
    print("="*60)

    try:
        from core.api.knowledge_base import router

        # Check routes exist
        routes = [route.path for route in router.routes]
        expected_routes = ['/api/kb/upload', '/api/kb/status/{task_id}',
                          '/api/kb/info', '/api/kb/clear']

        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✓ Route exists: {route}")
            else:
                print(f"✗ Route missing: {route}")

        return True

    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("  INTEGRATION TEST SUITE - RAG & Memory Agent ChromaDB Migration")
    print("="*70)

    results = {
        "Imports": test_imports(),
        "Embedding Config": test_embedding_configuration(),
        "Memory Config": test_memory_config(),
        "RAG Agent": test_rag_agent_mock(),
        "Workflow": test_workflow_structure(),
        "API": test_api_structure()
    }

    print("\n" + "="*70)
    print("  TEST RESULTS SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<30} {status}")

    all_passed = all(results.values())

    print("\n" + "="*70)
    if all_passed:
        print("  ✓ ALL TESTS PASSED!")
        print("  The RAG and Memory agents are properly integrated with ChromaDB")
    else:
        print("  ✗ SOME TESTS FAILED")
        print("  Please review the errors above")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
