"""
Supervisor node for LangGraph workflow
Fast rule-based routing with progress tracking
"""
from typing import Dict
from openai import OpenAI
import os
from utils.track_progress import progress_callbacks

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ===============================
# Supervisor Node
# ===============================

async def supervisor_node(state: Dict) -> Dict:
    """Supervisor with fast rule-based routing and progress tracking"""
    session_id = state.get("session_id", "")
    chat_mode = state.get("chat_mode", "general")

    await progress_callbacks.notify_progress(
        session_id,
        "supervisor",
        "active",
        "Analyzing request and routing..."
    )

    print("🧠 Supervisor: Making routing decision...")
    print(f"🔍 Supervisor received chat_mode: {chat_mode}")
    print(f"🔍 Supervisor received state keys: {list(state.keys())}")

    try:
        user_message = state['user_message'].lower()

        # Fast rule-based routing
        rag_keywords = [
            'search', 'find', 'document', 'file', 'pdf', 'image', 'upload',
            'retrieve', 'lookup', 'query', 'database', 'knowledge', 'source',
            'reference', 'cite', 'extract', 'analyze document'
        ]

        # Check chat mode first
        if chat_mode == 'rag' or chat_mode == 'my_resources':
            selected_agent = "rag_agent"
            reason = f"User mode: {chat_mode}"
            print(f"🎯 Routing to RAG (mode: {chat_mode})")
        elif any(keyword in user_message for keyword in rag_keywords):
            selected_agent = "rag_agent"
            reason = "Keyword match detected"
            print("🎯 Routing to RAG (keyword match)")
        else:
            selected_agent = "chatbot"
            reason = "General conversation"
            print("🎯 Routing to Chatbot (default)")

        # Prepare detailed message
        agent_names = {
            "rag_agent": "RAG Agent (Document Search)",
            "chatbot": "Chatbot Agent (Conversation & Wikipedia)"
        }
        detail_text = (
            f"Routed to: {agent_names.get(selected_agent, selected_agent)}"
            f" | {reason}"
        )

        await progress_callbacks.notify_progress(
            session_id,
            "supervisor",
            "completed",
            detail_text
        )

        return {
            **state,
            "selected_agent": selected_agent,
            "supervisor_decision": selected_agent,
            "decision_reason": reason
        }

    except Exception as e:
        print(f"❌ Supervisor error: {e}")
        await progress_callbacks.notify_progress(
            session_id,
            "supervisor",
            "error",
            f"Supervisor routing failed: {str(e)}"
        )
        return {
            **state,
            "selected_agent": "chatbot"
        }
