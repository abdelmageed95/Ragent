from typing import Dict
from rag_agent.ragagent import rag_answer
from utils.track_progress import progress_callbacks

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
    """Enhanced RAG agent with progress tracking"""
    session_id = state.get("session_id", "")
    
    await progress_callbacks.notify_progress(
        session_id, "agent", "active", "Searching documents and knowledge base..."
    )
    
    print("🔍 Enhanced RAG Agent Node: Processing document search...")
    
    try:
        if rag_answer is not None:
            try:
                response, metadata = rag_answer(
                    state["user_message"],
                    top_k_text=5,
                    top_k_image=5,
                    top_n=3
                )
                                
            
                detail_text = f"Found {metadata['hits_count']} relevant documents"
                if metadata["sources"]:
                    unique_sources = len(set(metadata["sources"]))
                    detail_text += f" from {unique_sources} sources"
                
                print(f"✅ Enhanced RAG Agent completed with {metadata['hits_count']} documents")
                
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
