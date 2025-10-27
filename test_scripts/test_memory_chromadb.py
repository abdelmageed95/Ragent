#!/usr/bin/env python3
"""
Test script for Memory Agent with ChromaDB backend

This script tests the migrated memory agent to ensure it works correctly
with ChromaDB instead of Qdrant.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory.mem_agent import MemoryAgent, MockMemoryAgent
from memory.mem_config import MemoryConfig


def test_memory_agent():
    """Test the memory agent with ChromaDB"""

    print("="*60)
    print("Testing Memory Agent with ChromaDB")
    print("="*60)

    # Test user and thread IDs
    user_id = "test_user_123"
    thread_id = "test_thread_456"

    try:
        # Initialize memory agent
        print("\n1. Initializing Memory Agent...")
        config = MemoryConfig()
        memory_agent = MemoryAgent(
            user_id=user_id,
            thread_id=thread_id,
            cfg=config
        )
        print(f"✅ Memory agent initialized successfully")
        print(f"   Collection: {memory_agent.collection_name}")
        print(f"   ChromaDB path: {config.chroma_db_dir}")

        # Test 1: Update memory with conversation
        print("\n2. Testing memory update...")
        user_msg = "Hello! My name is Alice and I'm a data scientist from New York."
        assistant_msg = "Nice to meet you, Alice! How can I help you today?"

        memory_agent.update_facts_and_embeddings(user_msg, assistant_msg)
        print("✅ Memory updated successfully")

        # Test 2: Fetch user facts
        print("\n3. Testing user facts retrieval...")
        facts = memory_agent.get_user_facts()
        print(f"✅ Retrieved {len(facts)} user facts:")
        for key, value in facts.items():
            print(f"   - {key}: {value}")

        # Test 3: Add another conversation
        print("\n4. Adding another conversation...")
        user_msg2 = "I need help with building a RAG system using Python."
        assistant_msg2 = "I'd be happy to help! RAG systems combine retrieval with generation."

        memory_agent.update_facts_and_embeddings(user_msg2, assistant_msg2)
        print("✅ Second conversation added")

        # Test 4: Query long-term memory
        print("\n5. Testing semantic search...")
        query = "Tell me about Alice's work"
        results = memory_agent.fetch_long_term(query=query, k=2)
        print(f"✅ Found {len(results)} relevant conversations:")
        for i, doc in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"   Content: {doc.page_content[:100]}...")
            print(f"   Metadata: {doc.metadata}")

        # Test 5: Fetch short-term memory
        print("\n6. Testing short-term memory fetch...")
        short_term = memory_agent.fetch_short_term()
        print(f"✅ Retrieved {len(short_term)} recent messages")

        # Test 6: Check collection stats
        print("\n7. Collection statistics...")
        count = memory_agent.collection.count()
        print(f"✅ Total documents in collection: {count}")

        print("\n" + "="*60)
        print("All tests passed! ✅")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_memory_agent():
    """Test the mock memory agent"""

    print("\n" + "="*60)
    print("Testing Mock Memory Agent")
    print("="*60)

    try:
        mock_agent = MockMemoryAgent()
        mock_agent.update_facts_and_embeddings(
            "Test message",
            "Test response"
        )
        print("✅ Mock memory agent works correctly")
        return True
    except Exception as e:
        print(f"❌ Mock memory agent test failed: {e}")
        return False


if __name__ == "__main__":
    # Test mock agent first (no dependencies)
    test_mock_memory_agent()

    # Test real memory agent
    success = test_memory_agent()

    if success:
        print("\n🎉 All memory agent tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
