from typing import Dict
from rag_agent.ragagent import rag_answer
from utils.track_progress import progress_callbacks

# Streaming helper function for RAG
async def send_streaming_response(session_id, partial_response, agent_type="rag_agent", tools_used=[]):
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

def rag_agent_node(state: Dict) -> Dict:
    """
    RAG agent node for document retrieval
    """
    print("🔍 RAG Agent Node: Processing document search...")
    
    try:
        # Try to use your existing rag_answer function
        try:
            
            response, metadata = rag_answer(
                state["user_message"],
                top_k_text=5,
                top_k_image=5,
                top_n=3
            )            
        except (ImportError, Exception) as rag_error:
            print(f"⚠️ RAG system unavailable: {rag_error}")
            response = "I apologize, but the document search system is currently unavailable. Please try again later or contact support if the issue persists."
            metadata = {
                "agent_type": "rag_agent",
                "hits_count": 0,
                "sources": [],
                "modalities": [],
                "rag_error": str(rag_error)
            }
        
        return {
            **state,
            "agent_response": response,
            "metadata": {**state.get("metadata", {}), **metadata}
        }
        
    except Exception as e:
        print(f"❌ RAG Agent error: {e}")
        error_msg = "I encountered an error searching the documents. Please try again."
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }


async def enhanced_rag_agent_node(state: Dict) -> Dict:
    """Enhanced RAG agent with progress tracking and memory context awareness"""
    session_id = state.get("session_id", "")
    
    await progress_callbacks.notify_progress(
        session_id, "agent", "active", "Searching documents and knowledge base..."
    )
    
    print("🔍 Enhanced RAG Agent Node: Processing document search with context awareness...")
    
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
                    facts_str = " | ".join([f"{k}: {v}" for k, v in user_facts.items()])
                    context_parts.append(f"User profile: {facts_str}")
                
                # Add recent conversation context
                short_term = memory_context.get("short_term", [])
                if short_term:
                    recent_context = " | ".join([
                        f"{msg['role']}: {msg['content'][:100]}..."
                        for msg in short_term[-3:]  # Last 3 messages
                        if msg['content'].strip()
                    ])
                    context_parts.append(f"Recent conversation: {recent_context}")
                
                # Create enhanced query with context
                if context_parts:
                    enhanced_query = f"Context: {' | '.join(context_parts)}\n\nCurrent question: {user_message}"
                else:
                    enhanced_query = user_message
                
                print(f"🧠 Using context-enhanced query (context parts: {len(context_parts)})")
                
                # Use standard RAG retrieval first
                response, metadata = rag_answer(
                    enhanced_query,
                    top_k_text=5,
                    top_k_image=5,
                    top_n=3
                )
                
                # Enhance the response with context awareness using a post-processing step
                if context_parts:
                    from openai import OpenAI
                    import os
                    
                    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    
                    context_enhancement_prompt = f"""
You are an AI assistant that enhances RAG responses with conversational context. 

Original user question: {user_message}
Available context: {' | '.join(context_parts)}
RAG response: {response}

Your task: Enhance the RAG response by:
1. Making it conversationally aware of the context
2. Personalizing it based on user facts (if relevant)
3. Referencing previous conversation if it adds value
4. Maintaining all the factual information from the RAG response
5. Making it feel like a natural continuation of the conversation

Important: Keep all document-based facts and sources. Just make the response more contextual and conversational.
"""
                    
                    try:
                        # First send the RAG response, then stream the enhancement
                        await send_streaming_response(session_id, response, "rag_agent", ["rag_retrieval"])
                        
                        # Stream the enhancement
                        enhanced_response = ""
                        for chunk in client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant that enhances RAG responses with conversational context."},
                                {"role": "user", "content": context_enhancement_prompt}
                            ],
                            temperature=0.3,
                            stream=True
                        ):
                            if chunk.choices[0].delta.content:
                                enhanced_response += chunk.choices[0].delta.content
                                await send_streaming_response(session_id, enhanced_response, "rag_agent", ["rag_retrieval", "context_enhancement"])
                        
                        response = enhanced_response if enhanced_response else response
                        print("✨ RAG response enhanced with conversational context")
                    except Exception as enhancement_error:
                        print(f"⚠️ Context enhancement failed, using original RAG response: {enhancement_error}")
                        # Send original RAG response if enhancement fails
                        await send_streaming_response(session_id, response, "rag_agent", ["rag_retrieval"])
                else:
                    # No context enhancement needed, just stream the RAG response
                    await send_streaming_response(session_id, response, "rag_agent", ["rag_retrieval"])
                
                # Update metadata to reflect context usage
                metadata.update({
                    "context_used": len(short_term),
                    "user_facts_count": len(user_facts),
                    "context_enhanced": len(context_parts) > 0
                })
                
                detail_text = f"Found {metadata['hits_count']} relevant documents"
                if metadata["sources"]:
                    unique_sources = len(set(metadata["sources"]))
                    detail_text += f" from {unique_sources} sources"
                if len(context_parts) > 0:
                    detail_text += f" | Enhanced with {len(context_parts)} context elements"
                
                print(f"✅ Enhanced RAG Agent completed with {metadata['hits_count']} documents and context awareness")
                
            except Exception as rag_error:
                print(f"⚠️ RAG system error: {rag_error}")
                response = "I apologize, but the document search system encountered an error. Please try again later."
                metadata = {
                    "agent_type": "rag_agent",
                    "hits_count": 0,
                    "sources": [],
                    "modalities": [],
                    "rag_error": str(rag_error)
                }
                detail_text = "Document search failed"
        else:
            print("⚠️ RAG system unavailable")
            response = "I apologize, but the document search system is currently unavailable."
            metadata = {
                "agent_type": "rag_agent",
                "hits_count": 0,
                "sources": [],
                "modalities": [],
                "system_unavailable": True
            }
            detail_text = "RAG system unavailable"
        
        await progress_callbacks.notify_progress(
            session_id, "agent", "completed", detail_text
        )
        
        return {
            **state,
            "agent_response": response,
            "metadata": {**state.get("metadata", {}), **metadata}
        }
        
    except Exception as e:
        print(f"❌ Enhanced RAG Agent error: {e}")
        await progress_callbacks.notify_progress(
            session_id, "agent", "error", f"RAG agent failed: {str(e)}"
        )
        error_msg = "I encountered an error searching the documents. Please try again."
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }
