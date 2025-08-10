from typing import Dict

from memory.mem_agent import MemoryAgent, MockMemoryAgent
from memory.mem_config import MemoryConfig
from utils.track_progress import progress_callbacks
# ===============================
# Memory Node
# ===============================
async def enhanced_memory_fetch_node(state: Dict) -> Dict:
    """Enhanced memory fetch with progress tracking"""
    session_id = state.get("session_id", "")
    
    # Notify start
    await progress_callbacks.notify_progress(
        session_id, "memory", "active", "Loading conversation context and user profile..."
    )
    
    print("📚 Enhanced Memory Fetch Node: Loading context...")
    
    try:
        # Try to use actual memory system
        if MemoryAgent and MemoryConfig:
            try:
                memory_agent = MemoryAgent(
                    user_id=state["user_id"],
                    thread_id=state["thread_id"],
                    cfg=MemoryConfig()
                )
                
                short_term = memory_agent.fetch_short_term()
                long_term = memory_agent.fetch_long_term(state["user_message"], k=5)
                user_facts = memory_agent.get_user_facts()
                
                print(f"✅ Real memory system: {len(short_term)} recent, {len(long_term)} relevant, {len(user_facts)} facts")
                
            except Exception as e:
                print(f"⚠️ Memory system error, using mock: {e}")
                memory_agent = MockMemoryAgent()
                short_term = []
                long_term = []
                user_facts = {}
        else:
            print("⚠️ Using mock memory system")
            memory_agent = MockMemoryAgent()
            short_term = []
            long_term = []
            user_facts = {}
        
        # Build context summary
        context_summary_parts = []
        if user_facts:
            facts_str = ", ".join([f"{k}: {v}" for k, v in list(user_facts.items())[:3]])
            context_summary_parts.append(f"User profile: {facts_str}")
        
        if long_term:
            context_summary_parts.append(f"Relevant past conversations ({len(long_term)} entries)")
        
        if short_term:
            context_summary_parts.append(f"Recent history ({len(short_term)} messages)")
        
        memory_context = {
            "short_term": short_term,
            "long_term": [doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in long_term],
            "user_facts": user_facts,
            "context_summary": " | ".join(context_summary_parts) if context_summary_parts else "No context available",
            "memory_agent": memory_agent
        }
        
        # Prepare detailed progress message
        details = []
        if short_term:
            details.append(f"{len(short_term)} recent messages")
        if long_term:
            details.append(f"{len(long_term)} relevant conversations")
        if user_facts:
            details.append(f"{len(user_facts)} user facts")
        
        detail_text = "Loaded: " + ", ".join(details) if details else "Memory context loaded"
        
        # Notify completion
        await progress_callbacks.notify_progress(
            session_id, "memory", "completed", detail_text
        )
        
        return {
            **state,
            "memory_context": memory_context
        }
        
    except Exception as e:
        print(f"❌ Enhanced memory fetch error: {e}")
        await progress_callbacks.notify_progress(
            session_id, "memory", "error", f"Memory fetch failed: {str(e)}"
        )
        return {
            **state,
            "memory_context": {"error": str(e)}
        }

def memory_fetch_node(state: Dict) -> Dict:
    """
    Node to fetch memory context at the start of workflow
    """
    print("📚 Memory Fetch Node: Loading context...")
    
    try:
        # Try to use your actual memory system
        try:
            memory_agent = MemoryAgent(
                user_id=state["user_id"],
                thread_id=state["thread_id"],
                cfg=MemoryConfig()
            )
            
            # Fetch all memory types
            short_term = memory_agent.fetch_short_term()
            long_term = memory_agent.fetch_long_term(state["user_message"], k=5)
            user_facts = memory_agent.get_user_facts()
            
        except (ImportError, Exception) as e:
            print(f"⚠️ Using mock memory system: {e}")
            # Mock memory system for testing
            memory_agent = MockMemoryAgent()
            short_term = []
            long_term = []
            user_facts = {}
        
        # Build context summary
        context_summary_parts = []
        if user_facts:
            facts_str = ", ".join([f"{k}: {v}" for k, v in list(user_facts.items())[:3]])
            context_summary_parts.append(f"User profile: {facts_str}")
        
        if long_term:
            context_summary_parts.append(f"Relevant past conversations ({len(long_term)} entries)")
        
        if short_term:
            context_summary_parts.append(f"Recent history ({len(short_term)} messages)")
        
        memory_context = {
            "short_term": short_term,
            "long_term": [doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in long_term],
            "user_facts": user_facts,
            "context_summary": " | ".join(context_summary_parts) if context_summary_parts else "No context available",
            "memory_agent": memory_agent  # Store for later use
        }
        
        print(f"✅ Memory loaded: {len(short_term)} recent, {len(long_term)} relevant, {len(user_facts)} facts")
        
        return {
            **state,
            "memory_context": memory_context
        }
        
    except Exception as e:
        print(f"❌ Memory fetch error: {e}")
        return {
            **state,
            "memory_context": {"error": str(e)}
        }

# ===============================
# Memory Update Node
# ===============================


async def enhanced_memory_update_node(state: Dict) -> Dict:
    """Enhanced memory update with progress tracking"""
    session_id = state.get("session_id", "")
    
    await progress_callbacks.notify_progress(
        session_id, "update", "active", "Saving conversation to memory system..."
    )
    
    print("💾 Enhanced Memory Update Node: Saving conversation...")
    
    try:
        memory_agent = state["memory_context"].get("memory_agent")
        if memory_agent:
            memory_agent.update(state["user_message"], state["agent_response"])
            
            detail_text = "Conversation saved to memory"
            await progress_callbacks.notify_progress(
                session_id, "update", "completed", detail_text
            )
            
            print("✅ Enhanced Memory updated successfully")
            return {
                **state,
                "metadata": {**state.get("metadata", {}), "memory_updated": True}
            }
        else:
            detail_text = "Memory update skipped (no agent available)"
            await progress_callbacks.notify_progress(
                session_id, "update", "completed", detail_text
            )
            
            print("⚠️ No memory agent available")
            return {
                **state,
                "metadata": {**state.get("metadata", {}), "memory_updated": False}
            }
            
    except Exception as e:
        print(f"❌ Enhanced Memory update error: {e}")
        await progress_callbacks.notify_progress(
            session_id, "update", "error", f"Memory update failed: {str(e)}"
        )
        return {
            **state,
            "metadata": {**state.get("metadata", {}), "memory_update_error": str(e)}
        }

def memory_update_node(state: Dict) -> Dict:
    """
    Node to update memory after agent processing
    """
    print("💾 Memory Update Node: Saving conversation...")
    
    try:
        memory_agent = state["memory_context"].get("memory_agent")
        if memory_agent:
            # Update memory with the conversation
            memory_agent.update(state["user_message"], state["agent_response"])
            
            print("✅ Memory updated successfully")
            return {
                **state,
                "metadata": {**state.get("metadata", {}), "memory_updated": True}
            }
        else:
            print("⚠️ No memory agent available")
            return {
                **state,
                "metadata": {**state.get("metadata", {}), "memory_updated": False}
            }
            
    except Exception as e:
        print(f"❌ Memory update error: {e}")
        return {
            **state,
            "metadata": {**state.get("metadata", {}), "memory_update_error": str(e)}
        }


