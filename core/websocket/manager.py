"""
Multi-Agent WebSocket Manager with Database Integration
"""
import json
from typing import Dict, Any
from datetime import datetime
from fastapi import WebSocket

from graph.workflow import LangGraphMultiAgentSystem, create_langgraph_system
from core.database.manager import DatabaseManager


class DatabaseAwareMultiAgentManager:
    """Multi-agent manager with database integration"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.langgraph_systems: Dict[str, LangGraphMultiAgentSystem] = {}
        self.memory_agents: Dict[str, Any] = {}  # Cache memory agents
        self.active_websockets: Dict[str, WebSocket] = {}

    def get_or_create_system(
        self,
        user_id: str,
        session_id: str
    ) -> LangGraphMultiAgentSystem:
        """Get or create LangGraph system for user session"""
        system_key = f"{user_id}:{session_id}"

        if system_key not in self.langgraph_systems:
            self.langgraph_systems[system_key] = create_langgraph_system(
                user_id=user_id,
                thread_id=session_id
            )
            print(f"🎯 Created LangGraph system for {system_key}")

        return self.langgraph_systems[system_key]
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        session_id: str,
        chat_mode: str = "general"
    ) -> Dict[str, Any]:
        """Process message with database tracking"""

        # Use the chat_mode passed from the WebSocket handler
        # (which gets it from the session_type in the database)
        session_mode = chat_mode  # "rag" or "general"

        print(f"📝 Session mode for routing: {session_mode}")

        # Get session from database to retrieve rag_mode (for RAG sessions)
        session = await self.db.get_session_by_id(session_id, user_id)
        rag_mode = session.get("rag_mode", "unified_kb") if session else "unified_kb"

        # Determine collection name for RAG queries
        if session_mode == "rag" and rag_mode == "specific_files":
            collection_name = f"session_{session_id}"
        else:
            collection_name = "documents"  # Unified KB

        print(f"📚 Collection: {collection_name} (mode: {rag_mode})")

        # Get system for this user session
        system = self.get_or_create_system(user_id, session_id)
        
        # Create WebSocket callback for progress and streaming
        async def websocket_callback(*args, **kwargs):
            websocket_key = f"{user_id}:{session_id}"
            if websocket_key not in self.active_websockets:
                return
                
            websocket = self.active_websockets[websocket_key]
            
            try:
                # Handle different callback types
                if len(args) >= 3:
                    session_id_cb, step, status = args[:3]
                    details = args[3] if len(args) > 3 else None
                    
                    # Check if this is a streaming response
                    if step == "streaming" and status == "partial" and details:
                        data = {
                            "type": "partial_response",
                            "message": details.get("partial_response", ""),
                            "agent_type": details.get("agent_type", "chatbot"),
                            "tools_used": details.get("tools_used", [])
                        }
                    else:
                        # Regular workflow update
                        data = {
                            "type": "workflow_update", 
                            "step": step,
                            "status": status,
                            "description": details
                        }
                else:
                    # Fallback for other callback formats
                    data = args[0] if args else kwargs.get('data', {})
                    
                await websocket.send_text(json.dumps(data))
            except Exception as e:
                print(f"WebSocket error for {websocket_key}: {e}")
        
        # Process with real workflow
        start_time = datetime.now()
        
        try:
            result = await system.process_with_progress_tracking(
                message, session_id, websocket_callback, session_mode, collection_name, rag_mode
            )
            
            # Update database
            tools_used = len(result.get("tools_used", []))
            await self.db.update_session_activity(
                session_id, 
                message_count_delta=1,
                tools_used_delta=tools_used
            )
            await self.db.update_user_activity(user_id, message_count_delta=1)
            
            # Save conversation to unified database
            await self.db.save_conversation_messages(
                session_id=session_id,
                user_id=user_id,
                thread_id=session_id,  # Use session_id as thread_id for consistency
                user_message=message,
                ai_response=result["response"],
                metadata=result["metadata"]
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Extract agent_type from metadata to top level for frontend
            agent_type = result.get("metadata", {}).get("agent_type", "chatbot")
            
            return {
                **result,
                "agent_type": agent_type,  # Make sure agent_type is at top level
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "user_id": user_id
            }
            
        except Exception as e:
            print(f"❌ Processing error for {session_id}: {e}")
            raise e