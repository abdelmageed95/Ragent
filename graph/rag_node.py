"""
RAG agent node for LangGraph workflow
Handles document search with progress tracking and context awareness
"""
from typing import Dict
from rag_agent.ragagent_simple import rag_answer
from utils.track_progress import progress_callbacks


# Streaming helper function for RAG
async def send_streaming_response(
    session_id,
    partial_response,
    agent_type="rag_agent",
    tools_used=[]
):
    """Send a partial response via progress callback for streaming"""
    try:
        await progress_callbacks.notify_progress(
            session_id, "streaming", "partial", {
                "partial_response": partial_response,
                "agent_type": agent_type,
                "tools_used": tools_used
            }
        )
    except Exception as e:
        print(f"Error sending streaming response: {e}")


# ===============================
# RAG Agent Node
# ===============================

async def rag_agent_node(state: Dict) -> Dict:
    """RAG agent with progress tracking and memory context awareness"""
    session_id = state.get("session_id", "")

    # Determine collection name based on session rag_mode
    # This needs to be passed from the WebSocket handler
    collection_name = state.get("collection_name", "documents")
    rag_mode = state.get("rag_mode", "unified_kb")

    mode_emoji = "📁" if rag_mode == "specific_files" else "🗄️"
    print(f"{mode_emoji} RAG Mode: {rag_mode}, Collection: {collection_name}")

    await progress_callbacks.notify_progress(
        session_id,
        "agent",
        "active",
        f"Searching {rag_mode} knowledge base..."
    )

    print(
        f"🔍 RAG Agent Node: Processing document search with context awareness... (collection: {collection_name})"
    )

    try:
        if rag_answer is not None:
            try:
                # Get memory context to make RAG context-aware
                memory_context = state.get("memory_context", {})
                user_message = state["user_message"]

                # Build context-aware query
                context_parts = []

                # Add user facts if available
                user_facts = memory_context.get("user_facts", {})
                if user_facts:
                    facts_str = " | ".join([
                        f"{k}: {v}"
                        for k, v in user_facts.items()
                    ])
                    context_parts.append(f"User profile: {facts_str}")

                # Add recent conversation context
                short_term = memory_context.get("short_term", [])
                if short_term:
                    recent_context = " | ".join([
                        f"{msg['role']}: {msg['content'][:100]}..."
                        for msg in short_term[-3:]  # Last 3 messages
                        if msg['content'].strip()
                    ])
                    context_parts.append(
                        f"Recent conversation: {recent_context}"
                    )

                # Create enhanced query with context
                if context_parts:
                    enhanced_query = (
                        f"Context: {' | '.join(context_parts)}\n\n"
                        f"Current question: {user_message}"
                    )
                else:
                    enhanced_query = user_message

                print(
                    f"🧠 Using context-enhanced query "
                    f"(context parts: {len(context_parts)})"
                )

                # Use standard RAG retrieval with collection_name
                response, metadata = rag_answer(
                    enhanced_query,
                    top_k=5,
                    collection_name=collection_name
                )

                # Stream the RAG response
                await send_streaming_response(
                    session_id,
                    response,
                    "rag_agent",
                    ["rag_retrieval"]
                )

                # Simple context integration
                if context_parts:
                    print(
                        "✨ RAG response includes conversational "
                        "context awareness"
                    )
                    metadata["context_enhanced"] = True

                # Update metadata to reflect context usage
                metadata.update({
                    "context_used": len(short_term),
                    "user_facts_count": len(user_facts),
                    "context_enhanced": len(context_parts) > 0
                })

                # Add agent_type to metadata if not present
                if "agent_type" not in metadata:
                    metadata["agent_type"] = "rag_agent"

                print(
                    f"🔍 RAG agent setting metadata agent_type: "
                    f"{metadata.get('agent_type')}"
                )

                chunks_found = metadata.get('chunks_found', 0)
                detail_text = f"Found {chunks_found} relevant documents"
                if metadata.get("sources"):
                    unique_sources = len(set(metadata["sources"]))
                    detail_text += f" from {unique_sources} sources"
                if len(context_parts) > 0:
                    detail_text += (
                        f" | Enhanced with {len(context_parts)} "
                        f"context elements"
                    )

                print(
                    f"✅ RAG Agent completed with {chunks_found} documents "
                    f"and context awareness"
                )

            except Exception as rag_error:
                print(f"⚠️  RAG system error: {rag_error}")
                response = (
                    "I apologize, but the document search system "
                    "encountered an error. Please try again later."
                )
                metadata = {
                    "agent_type": "rag_agent",
                    "chunks_found": 0,
                    "sources": [],
                    "rag_error": str(rag_error)
                }
                detail_text = "Document search failed"
        else:
            print("⚠️  RAG system unavailable")
            response = (
                "I apologize, but the document search system "
                "is currently unavailable."
            )
            metadata = {
                "agent_type": "rag_agent",
                "chunks_found": 0,
                "sources": [],
                "system_unavailable": True
            }
            detail_text = "RAG system unavailable"

        await progress_callbacks.notify_progress(
            session_id,
            "agent",
            "completed",
            detail_text
        )

        return {
            **state,
            "agent_response": response,
            "metadata": {**state.get("metadata", {}), **metadata}
        }

    except Exception as e:
        print(f"❌ RAG Agent error: {e}")
        await progress_callbacks.notify_progress(
            session_id,
            "agent",
            "error",
            f"RAG agent failed: {str(e)}"
        )
        error_msg = (
            "I encountered an error searching the documents. "
            "Please try again."
        )
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }
