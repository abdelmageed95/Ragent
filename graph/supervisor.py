from typing import Dict
from openai import OpenAI
import os
from utils.track_progress import progress_callbacks

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ===============================
# Supervisor Node
# ===============================

def supervisor_node(state: Dict) -> Dict:
    """
    Supervisor node that decides which agent to route to
    """
    print("🧠 Supervisor Node: Making routing decision...")
    
    # Build routing prompt
    routing_prompt = f"""
    Analyze this user request and route to the appropriate agent:
    
    User message: {state['user_message']}
    Context: {state['memory_context'].get('context_summary', 'None')}
    
    Available agents:
    1. rag_agent - For document search, retrieving information from uploaded files/images
    2. chatbot - For general conversation, personal questions, advice, casual chat
    
    Consider:
    - Does the user want to search documents/files? → rag_agent
    - Is this a general conversation or question? → chatbot
    
    Return ONLY: rag_agent OR chatbot
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a routing supervisor. Return only the agent name."},
                {"role": "user", "content": routing_prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        agent_choice = response.choices[0].message.content.strip().lower()
        
        # Validate choice
        if "rag" in agent_choice:
            selected_agent = "rag_agent"
        else:
            selected_agent = "chatbot"  # Default to chatbot
        
        print(f"🎯 Supervisor decision: {selected_agent}")
        
        return {
            **state,
            "selected_agent": selected_agent
        }
        
    except Exception as e:
        print(f"❌ Supervisor error: {e}")
        return {
            **state,
            "selected_agent": "chatbot"  # Fallback
        }


async def enhanced_supervisor_node(state: Dict) -> Dict:
    """Enhanced supervisor with progress tracking"""
    session_id = state.get("session_id", "")
    chat_mode = state.get("chat_mode", "general")

    await progress_callbacks.notify_progress(
        session_id, "supervisor", "active", "Analyzing request intent and routing to appropriate agent..."
    )

    print("🧠 Enhanced Supervisor Node: Making routing decision...")

    # Use explicit mode selection if provided
    if chat_mode == "rag":
        print("🎯 Enhanced Supervisor decision: rag_agent (user selected 'My Resources')")
        decision = "rag_agent"
        await progress_callbacks.notify_progress(
            session_id, "supervisor", "completed", "Routed to RAG agent (user preference)"
        )

        return {
            **state,
            "selected_agent": decision,
            "supervisor_decision": decision,
            "decision_reason": "User selected 'My Resources' mode"
        }
    elif chat_mode == "general":
        print("🎯 Enhanced Supervisor decision: chatbot (user selected 'General')")
        decision = "chatbot"
        await progress_callbacks.notify_progress(
            session_id, "supervisor", "completed", "Routed to chatbot (user preference)"
        )

        return {
            **state,
            "selected_agent": decision,
            "supervisor_decision": decision,
            "decision_reason": "User selected 'General' mode"
        }

    # Fallback to AI-based routing for backward compatibility
    routing_prompt = f"""
    Analyze this user request and route to the appropriate agent:
    
    User message: {state['user_message']}
    Context: {state['memory_context'].get('context_summary', 'None')}
    
    Available agents:
    1. rag_agent - For document search, retrieving information from uploaded files/images
    2. chatbot - For general conversation, personal questions, advice, casual chat
    
    Consider:
    - Does the user want to search documents/files? → rag_agent
    - Is this a general conversation or question? → chatbot
    
    Return ONLY: rag_agent OR chatbot
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a routing supervisor. Return only the agent name."},
                {"role": "user", "content": routing_prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )

        agent_choice = response.choices[0].message.content.strip().lower()

        if "rag" in agent_choice:
            selected_agent = "rag_agent"
        else:
            selected_agent = "chatbot"

        print(f"🎯 Enhanced Supervisor decision: {selected_agent}")

        # Prepare detailed message
        agent_names = {
            "rag_agent": "RAG Agent (Document Search)",
            "chatbot": "Chatbot Agent (Conversation & Wikipedia)"
        }
        detail_text = f"Routed to: {agent_names.get(selected_agent, selected_agent)}"

        await progress_callbacks.notify_progress(
            session_id, "supervisor", "completed", detail_text
        )

        return {
            **state,
            "selected_agent": selected_agent
        }

    except Exception as e:
        print(f"❌ Enhanced Supervisor error: {e}")
        await progress_callbacks.notify_progress(
            session_id, "supervisor", "error", f"Supervisor routing failed: {str(e)}"
        )
        return {
            **state,
            "selected_agent": "chatbot"
        }
