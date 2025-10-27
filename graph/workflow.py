"""
LangGraph Multi-Agent Workflow System
Includes progress tracking, memory, RAG, chat agents, and guardrails
"""
import os
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from typing import Dict, Any, Literal

from graph.memory_nodes import memory_update_node, memory_fetch_node
from graph.rag_node import rag_agent_node
from graph.chat_node import chatbot_agent_node
from graph.guardrails_nodes import (
    input_guardrails_node,
    output_guardrails_node,
    should_continue_after_validation
)
from utils.track_progress import progress_callbacks
from core.config import Config


# Disable LangSmith tracing to avoid API errors
os.environ["LANGCHAIN_TRACING_V2"] = "false"


# ===============================
# Conditional Edge Functions
# ===============================

def route_by_session_mode(state: Dict) -> Literal["rag_agent", "chatbot"]:
    """
    Route based on session mode (no supervisor needed)

    Session modes:
    - "rag": Route to RAG agent for document Q&A
    - "general" or "ai": Route to chatbot for conversational AI with tools
    """
    session_mode = state.get("session_mode", "general")

    if session_mode == "rag":
        print("🔀 Routing to RAG Agent (RAG mode)")
        return "rag_agent"
    else:
        print("🔀 Routing to Chatbot Agent (Chatbot mode)")
        return "chatbot"


# ===============================
# LangGraph Workflow System
# ===============================

class LangGraphMultiAgentSystem:
    """
    LangGraph multi-agent system with progress tracking and guardrails
    """

    def __init__(self, user_id: str, thread_id: str = "default"):
        self.user_id = user_id
        self.thread_id = thread_id
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the LangGraph workflow with guardrails"""
        workflow = StateGraph(dict)

        # Add nodes (with guardrails if enabled)
        if Config.ENABLE_GUARDRAILS:
            workflow.add_node("input_guardrails", input_guardrails_node)
            workflow.add_node("output_guardrails", output_guardrails_node)

        # Add core workflow nodes (supervisor removed - using session mode routing)
        workflow.add_node("memory_fetch", memory_fetch_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("chatbot", chatbot_agent_node)
        workflow.add_node("memory_update", memory_update_node)

        # Build workflow with guardrails
        if Config.ENABLE_GUARDRAILS:
            # Start with input validation
            workflow.add_edge(START, "input_guardrails")

            # Conditional edge after validation
            workflow.add_conditional_edges(
                "input_guardrails",
                should_continue_after_validation,
                {
                    "continue": "memory_fetch",
                    "end": "output_guardrails"
                }
            )

            # Route directly by session mode (no supervisor)
            workflow.add_conditional_edges(
                "memory_fetch",
                route_by_session_mode,
                {
                    "rag_agent": "rag_agent",
                    "chatbot": "chatbot"
                }
            )
        else:
            # No guardrails - direct to memory fetch
            workflow.add_edge(START, "memory_fetch")

            # Route directly by session mode (no supervisor)
            workflow.add_conditional_edges(
                "memory_fetch",
                route_by_session_mode,
                {
                    "rag_agent": "rag_agent",
                    "chatbot": "chatbot"
                }
            )

        # Route through guardrails if enabled
        if Config.ENABLE_GUARDRAILS:
            workflow.add_edge("rag_agent", "output_guardrails")
            workflow.add_edge("chatbot", "output_guardrails")
            workflow.add_edge("output_guardrails", "memory_update")
        else:
            workflow.add_edge("rag_agent", "memory_update")
            workflow.add_edge("chatbot", "memory_update")

        workflow.add_edge("memory_update", END)

        return workflow.compile()

    async def process_with_progress_tracking(
        self,
        user_message: str,
        session_id: str,
        progress_callback=None,
        session_mode: str = "general",  # "rag" or "general"
        collection_name: str = "documents",  # ChromaDB collection name
        rag_mode: str = "unified_kb"  # "specific_files" or "unified_kb"
    ) -> Dict[str, Any]:
        """
        Process a message with real-time progress tracking

        Args:
            user_message: The user's input message
            session_id: Session ID for progress tracking
            progress_callback: Optional callback for progress updates
            session_mode: Session mode - "rag" for RAG agent, "general" for chatbot
            collection_name: ChromaDB collection name for RAG queries
            rag_mode: RAG mode - "specific_files" or "unified_kb"
        """
        mode_emoji = "📚" if session_mode == "rag" else "💬"
        print(
            f"\n🚀 LangGraph Workflow ({mode_emoji} {session_mode}): "
            f"{user_message[:50]}..."
        )

        # Register progress callback if provided
        if progress_callback:
            progress_callbacks.register_callback(
                session_id,
                progress_callback
            )

        # Initial state with session_id and session_mode for routing
        initial_state = {
            "user_message": user_message,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "session_id": session_id,
            "session_mode": session_mode,  # Used for routing
            "collection_name": collection_name,  # For RAG queries
            "rag_mode": rag_mode,  # RAG mode type
            "messages": [HumanMessage(content=user_message)],
            "memory_context": {},
            "selected_agent": "",  # Legacy field, kept for compatibility
            "agent_response": "",
            "metadata": {},
            "tools_used": [],
            "tool_results": [],  # Renamed from wikipedia_results
            "wikipedia_results": []  # Keep for backward compatibility
        }

        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)

            print("🎉 LangGraph Workflow completed")

            # Determine which agent was used based on session_mode
            agent_used = "rag_agent" if session_mode == "rag" else "chatbot"

            return {
                "response": final_state["agent_response"],
                "agent_used": agent_used,
                "metadata": final_state["metadata"],
                "tools_used": final_state["tools_used"],
                "tool_results": final_state.get("tool_results", []),
                "wikipedia_results": final_state.get("wikipedia_results", []),
                "memory_context_summary": final_state["memory_context"].get(
                    "context_summary", ""
                )
            }

        except Exception as e:
            print(f"💥 LangGraph Workflow error: {e}")
            await progress_callbacks.notify_progress(
                session_id,
                "error",
                "error",
                f"Workflow failed: {str(e)}"
            )

            return {
                "response": (
                    "I encountered an error processing your request. "
                    "Please try again."
                ),
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
        """Synchronous process method for compatibility"""
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
                "memory_context_summary": final_state["memory_context"].get(
                    "context_summary", ""
                )
            }

        except Exception as e:
            print(f"💥 LangGraph Workflow error (sync): {e}")
            return {
                "response": (
                    "I encountered an error processing your request. "
                    "Please try again."
                ),
                "agent_used": "error",
                "metadata": {"error": str(e)},
                "tools_used": [],
                "wikipedia_results": [],
                "memory_context_summary": ""
            }


# ===============================
# Convenience Functions
# ===============================

def create_langgraph_system(
    user_id: str,
    thread_id: str = "default"
) -> LangGraphMultiAgentSystem:
    """Create a new LangGraph-based system"""
    return LangGraphMultiAgentSystem(user_id=user_id, thread_id=thread_id)


def create_agentic_system(
    user_id: str,
    thread_id: str = "default"
) -> LangGraphMultiAgentSystem:
    """Alias for create_langgraph_system"""
    return create_langgraph_system(user_id=user_id, thread_id=thread_id)


async def chat_with_langgraph(
    system: LangGraphMultiAgentSystem,
    message: str,
    session_id: str = "test"
) -> Dict[str, Any]:
    """Chat interface with progress tracking"""

    def progress_printer(session_id, step, status, details):
        status_emoji = {"active": "🔄", "completed": "✅", "error": "❌"}
        emoji = status_emoji.get(status, "📊")
        print(f"{emoji} [{step.upper()}] {status}: {details}")

    result = await system.process_with_progress_tracking(
        message,
        session_id,
        progress_printer
    )

    print(f"\n🤖 Agent ({result['agent_used']}): {result['response']}")

    if result['tools_used']:
        print(f"🛠️  Tools used: {', '.join(result['tools_used'])}")

    if result['wikipedia_results']:
        print(f"📖 Wikipedia searches: {len(result['wikipedia_results'])}")

    print(f"📊 Context: {result['memory_context_summary']}")

    return result


def run_workflow(
    system: LangGraphMultiAgentSystem,
    message: str
) -> Dict[str, Any]:
    """Simple synchronous chat interface"""
    result = system.process(message)

    print(f"\n🤖 Agent ({result['agent_used']}): {result['response']}")

    if result['tools_used']:
        print(f"🛠️  Tools used: {', '.join(result['tools_used'])}")

    if result['wikipedia_results']:
        print(f"📖 Wikipedia searches: {len(result['wikipedia_results'])}")
        for wiki_result in result['wikipedia_results']:
            print(
                f"   - {wiki_result['tool']}: {wiki_result['query']}"
            )

    print(f"📊 Context: {result['memory_context_summary']}")

    return result
