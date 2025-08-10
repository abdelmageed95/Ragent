import os
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from typing import Dict, Any, Literal

from graph.memory_nodes import (memory_update_node, memory_fetch_node, 
                                enhanced_memory_fetch_node,
                                enhanced_memory_update_node)
from graph.supervisor import supervisor_node,enhanced_supervisor_node
from graph.rag_node import rag_agent_node, enhanced_rag_agent_node
from graph.chat_node import chatbot_agent_node, enhanced_chatbot_agent_node
from utils.track_progress import progress_callbacks


# Disable LangSmith tracing to avoid API errors
os.environ["LANGCHAIN_TRACING_V2"] = "false"


# ===============================
# Conditional Edge Functions
# ===============================

def route_to_agent(state: Dict) -> Literal["rag_agent", "chatbot"]:
    """
    Route to the selected agent
    """
    return state["selected_agent"]


# ===============================
# LangGraph Workflow Builder
# ===============================

class LangGraphMultiAgentSystem:
    """
    LangGraph-based multi-agent system with Wikipedia tools
    """
    
    def __init__(self, user_id: str, thread_id: str = "default"):
        self.user_id = user_id
        self.thread_id = thread_id
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """
        Build the LangGraph workflow
        """
        # Create the graph
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("memory_fetch", memory_fetch_node)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("chatbot", chatbot_agent_node)
        workflow.add_node("memory_update", memory_update_node)
        
        # Add edges following the flowchart
        workflow.add_edge(START, "memory_fetch")
        workflow.add_edge("memory_fetch", "supervisor")
        
        # Conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            route_to_agent,
            {
                "rag_agent": "rag_agent",
                "chatbot": "chatbot"
            }
        )
        
        # Both agents go to memory update
        workflow.add_edge("rag_agent", "memory_update")
        workflow.add_edge("chatbot", "memory_update")
        workflow.add_edge("memory_update", END)
        
        # Compile the workflow
        return workflow.compile()
    
    def process(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message through the workflow
        """
        print(f"\n🚀 LangGraph Workflow: {user_message[:50]}...")
        
        # Initial state
        initial_state = {
            "user_message": user_message,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "messages": [HumanMessage(content=user_message)],
            "memory_context": {},
            "selected_agent": "",
            "agent_response": "",
            "metadata": {},
            "tools_used": [],
            "wikipedia_results": []
        }
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            print("🎉 LangGraph Workflow completed")
            
            return {
                "response": final_state["agent_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": final_state["metadata"],
                "tools_used": final_state["tools_used"],
                "wikipedia_results": final_state["wikipedia_results"],
                "memory_context_summary": final_state["memory_context"].get("context_summary", "")
            }
            
        except Exception as e:
            print(f"💥 LangGraph Workflow error: {e}")
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "agent_used": "error",
                "metadata": {"error": str(e)},
                "tools_used": [],
                "wikipedia_results": [],
                "memory_context_summary": ""
            }



class EnhancedLangGraphMultiAgentSystem:
    """Enhanced LangGraph-based multi-agent system with real-time progress tracking"""
    
    def __init__(self, user_id: str, thread_id: str = "default"):
        self.user_id = user_id
        self.thread_id = thread_id
        self.workflow = self._build_enhanced_workflow()
    
    def _build_enhanced_workflow(self):
        """Build the enhanced LangGraph workflow with progress tracking"""
        workflow = StateGraph(dict)
        
        # Add enhanced nodes
        workflow.add_node("memory_fetch", enhanced_memory_fetch_node)
        workflow.add_node("supervisor", enhanced_supervisor_node)
        workflow.add_node("rag_agent", enhanced_rag_agent_node)
        workflow.add_node("chatbot", enhanced_chatbot_agent_node)
        workflow.add_node("memory_update", enhanced_memory_update_node)
        
        # Add edges
        workflow.add_edge(START, "memory_fetch")
        workflow.add_edge("memory_fetch", "supervisor")
        
        workflow.add_conditional_edges(
            "supervisor",
            route_to_agent,
            {
                "rag_agent": "rag_agent",
                "chatbot": "chatbot"
            }
        )
        
        workflow.add_edge("rag_agent", "memory_update")
        workflow.add_edge("chatbot", "memory_update")
        workflow.add_edge("memory_update", END)
        
        return workflow.compile()
    
    async def process_with_progress_tracking(
        self, user_message: str, session_id: str, progress_callback=None, chat_mode: str = "general"
    ) -> Dict[str, Any]:
        """Process a user message with real-time progress tracking"""
        print(f"\n🚀 Enhanced LangGraph Workflow: {user_message[:50]}...")
        
        # Register progress callback if provided
        if progress_callback:
            progress_callbacks.register_callback(session_id, progress_callback)
        
        # Initial state with session_id for tracking
        initial_state = {
            "user_message": user_message,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "session_id": session_id,  # Critical for progress tracking
            "chat_mode": chat_mode,  # Add chat mode for supervisor routing
            "messages": [HumanMessage(content=user_message)],
            "memory_context": {},
            "selected_agent": "",
            "agent_response": "",
            "metadata": {},
            "tools_used": [],
            "wikipedia_results": []
        }
        
        try:
            # Run the enhanced workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            print("🎉 Enhanced LangGraph Workflow completed")
            
            return {
                "response": final_state["agent_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": final_state["metadata"],
                "tools_used": final_state["tools_used"],
                "wikipedia_results": final_state["wikipedia_results"],
                "memory_context_summary": final_state["memory_context"].get("context_summary", "")
            }
            
        except Exception as e:
            print(f"💥 Enhanced LangGraph Workflow error: {e}")
            await progress_callbacks.notify_progress(session_id, "error", "error", f"Workflow failed: {str(e)}")
            
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "agent_used": "error",
                "metadata": {"error": str(e)},
                "tools_used": [],
                "wikipedia_results": [],
                "memory_context_summary": ""
            }
        finally:
            # Clean up callbacks
            progress_callbacks.unregister_session(session_id)
    
    def process(self, user_message: str) -> Dict[str, Any]:
        """Legacy synchronous process method for compatibility"""
        print(f"\n🚀 LangGraph Workflow (sync): {user_message[:50]}...")
        
        initial_state = {
            "user_message": user_message,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "session_id": "",  # No session tracking for sync
            "messages": [HumanMessage(content=user_message)],
            "memory_context": {},
            "selected_agent": "",
            "agent_response": "",
            "metadata": {},
            "tools_used": [],
            "wikipedia_results": []
        }
        
        try:
            # Use synchronous invoke
            final_state = self.workflow.invoke(initial_state)
            
            print("🎉 LangGraph Workflow completed (sync)")
            
            return {
                "response": final_state["agent_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": final_state["metadata"],
                "tools_used": final_state["tools_used"],
                "wikipedia_results": final_state["wikipedia_results"],
                "memory_context_summary": final_state["memory_context"].get("context_summary", "")
            }
            
        except Exception as e:
            print(f"💥 LangGraph Workflow error (sync): {e}")
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "agent_used": "error",
                "metadata": {"error": str(e)},
                "tools_used": [],
                "wikipedia_results": [],
                "memory_context_summary": ""
            }
# ===============================
# Convenience Functions
# ===============================

def create_agentic_system(user_id: str, thread_id: str = "default"):
    """Create a new LangGraph-based system"""
    return LangGraphMultiAgentSystem(user_id=user_id, thread_id=thread_id)

def run_workflow(system: LangGraphMultiAgentSystem, message: str):
    """Simple chat interface for LangGraph system"""
    result = system.process(message)
    
    print(f"\n🤖 Agent ({result['agent_used']}): {result['response']}")
    
    if result['tools_used']:
        print(f"🛠️ Tools used: {', '.join(result['tools_used'])}")
    
    if result['wikipedia_results']:
        print(f"📖 Wikipedia searches: {len(result['wikipedia_results'])}")
        for wiki_result in result['wikipedia_results']:
            print(f"   - {wiki_result['tool']}: {wiki_result['query']}")
    
    print(f"📊 Context: {result['memory_context_summary']}")
    
    return result


def create_enhanced_langgraph_system(user_id: str, thread_id: str = "default"):
    """Create a new enhanced LangGraph-based system"""
    return EnhancedLangGraphMultiAgentSystem(user_id=user_id, thread_id=thread_id)

# For backward compatibility
def create_langgraph_system(user_id: str, thread_id: str = "default"):
    """Backward compatible function"""
    return create_enhanced_langgraph_system(user_id=user_id, thread_id=thread_id)

async def chat_with_enhanced_langgraph(system: EnhancedLangGraphMultiAgentSystem, message: str, session_id: str = "test"):
    """Enhanced chat interface with progress tracking"""
    
    def progress_printer(session_id, step, status, details):
        status_emoji = {"active": "🔄", "completed": "✅", "error": "❌"}
        print(f"{status_emoji.get(status, '📊')} [{step.upper()}] {status}: {details}")
    
    result = await system.process_with_progress_tracking(message, session_id, progress_printer)
    
    print(f"\n🤖 Agent ({result['agent_used']}): {result['response']}")
    
    if result['tools_used']:
        print(f"🛠️ Tools used: {', '.join(result['tools_used'])}")
    
    if result['wikipedia_results']:
        print(f"📖 Wikipedia searches: {len(result['wikipedia_results'])}")
    
    print(f"📊 Context: {result['memory_context_summary']}")
    
    return result

# ===============================
# Example Usage
# ===============================
"""
if __name__ == "__main__":
    import asyncio
    
    print("=== Enhanced LangGraph Multi-Agent System with Real-Time Progress ===")
    
    async def test_enhanced_system():
        # Create the enhanced system
        system = create_enhanced_langgraph_system(user_id="alice123", thread_id="enhanced_session")
        
        # Test messages
        test_messages = [
            "Hello, I'm Alice, interested in AI research",
            "Tell me about machine learning from Wikipedia",
            "Search for documents about neural networks",
            "What's the history of artificial intelligence?"
        ]
        
        for i, message in enumerate(test_messages):
            print(f"\n{'='*80}")
            print(f"👤 User: {message}")
            result = await chat_with_enhanced_langgraph(system, message, f"test_session_{i}")
            
            # Show metadata
            print(f"📋 Metadata: {json.dumps(result['metadata'], indent=2)}")
    
    # Run the test
    asyncio.run(test_enhanced_system())

"""