#!/usr/bin/env python3
"""
Test Memory Agent in Full Workflow

This simulates what happens when a user sends a message through the UI.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_workflow():
    """Test the full workflow with memory"""
    from graph.workflow import create_enhanced_langgraph_system

    print("="*60)
    print("Testing Full Workflow with Memory")
    print("="*60)

    # Use real user from database
    user_id = "68f287a01dded3618fb32b2c"
    session_id = "68f288dcf171989a4fbd9f1f"

    print(f"\nUser ID: {user_id}")
    print(f"Session ID: {session_id}")

    # Create system
    system = create_enhanced_langgraph_system(user_id, session_id)
    print("✓ System created")

    # Test message
    test_message = "My name is Sarah and I work as a data scientist in San Francisco. I love Python and machine learning."

    print(f"\nTest message: {test_message}")
    print("\nProcessing through workflow...")
    print("-"*60)

    try:
        result = await system.process_with_progress_tracking(
            test_message,
            session_id,
            progress_callback=None,
            chat_mode="general"
        )

        print("-"*60)
        print("\n✓ Workflow completed!")
        print(f"\nResponse: {result['response'][:200]}...")
        print(f"\nAgent used: {result.get('agent_used', 'unknown')}")
        print(f"Metadata: {result.get('metadata', {})}")

        # Now check if facts were saved
        print("\n" + "="*60)
        print("Checking if facts were saved...")
        print("="*60)

        from memory.mem_agent import MemoryAgent
        agent = MemoryAgent(user_id, session_id)

        facts = agent.get_user_facts()
        print(f"\nUser facts in database: {facts}")

        if facts:
            print("✓ SUCCESS! Facts were saved!")
        else:
            print("✗ FAILED! No facts found in database")

        # Check long-term memory
        print("\nChecking long-term memory (ChromaDB)...")
        count = agent.collection.count()
        print(f"Documents in ChromaDB: {count}")

        if count > 0:
            print("✓ Long-term memory stored in ChromaDB")

            # Try semantic search
            results = agent.fetch_long_term("Tell me about Sarah", k=2)
            print(f"\nSemantic search results: {len(results)} found")
            if results:
                print(f"  First result: {results[0].page_content[:100]}...")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_workflow())
