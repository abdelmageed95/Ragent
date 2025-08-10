"""
FastAPI Backend with Real LangGraph Workflow Integration
Hooks into actual workflow steps for live progress updates
"""

import os
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Import your existing multi-agent system

from graph.workflow import LangGraphMultiAgentSystem, create_langgraph_system
from graph.memory_nodes import enhanced_memory_fetch_node, enhanced_memory_update_node
from graph.supervisor import enhanced_supervisor_node
from graph.rag_node import enhanced_rag_agent_node
from graph.chat_node import enhanced_chatbot_agent_node
# ===============================
# Workflow Progress Tracker
# ===============================

class WorkflowProgressTracker:
    """Tracks workflow progress and sends real-time updates"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
    
    def register_session(self, session_id: str, websocket_manager):
        """Register a session for progress tracking"""
        self.active_sessions[session_id] = {
            "websocket_manager": websocket_manager,
            "current_step": None,
            "start_time": datetime.now(),
            "steps_completed": []
        }
    
    def unregister_session(self, session_id: str):
        """Unregister a session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.progress_callbacks:
            del self.progress_callbacks[session_id]
    
    async def update_step(self, session_id: str, step_name: str, status: str, details: str = None):
        """Update workflow step progress"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session["current_step"] = step_name
        
        if status == "completed":
            session["steps_completed"].append(step_name)
        
        # Send WebSocket update
        websocket_manager = session["websocket_manager"]
        await websocket_manager.send_workflow_update(session_id, step_name, status, details)
        
        print(f"📊 Workflow Progress [{session_id}]: {step_name} -> {status}")

# Global progress tracker
progress_tracker = WorkflowProgressTracker()

# ===============================
# Workflow Node Decorators
# ===============================

def track_workflow_step(step_name: str, description: str = None):
    """Decorator to track workflow step execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(state: Dict, session_id: str = None) -> Dict:
            # Start step
            if session_id:
                await progress_tracker.update_step(
                    session_id, step_name, "active", description or f"Executing {step_name}..."
                )
            
            try:
                # Execute the actual function
                if asyncio.iscoroutinefunction(func):
                    result = await func(state)
                else:
                    result = func(state)
                
                # Complete step
                if session_id:
                    await progress_tracker.update_step(
                        session_id, step_name, "completed", f"{step_name.title()} completed successfully"
                    )
                
                return result
                
            except Exception as e:
                # Error step
                if session_id:
                    await progress_tracker.update_step(
                        session_id, step_name, "error", f"Error in {step_name}: {str(e)}"
                    )
                raise e
        
        @wraps(func)
        def sync_wrapper(state: Dict, session_id: str = None) -> Dict:
            # For synchronous functions, we can't send real-time updates
            # but we can still track progress
            try:
                result = func(state)
                print(f"✅ {step_name} completed (sync)")
                return result
            except Exception as e:
                print(f"❌ {step_name} failed: {e}")
                raise e
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# ===============================
# Enhanced Multi-Agent System
# ===============================

class EnhancedLangGraphMultiAgentSystem(LangGraphMultiAgentSystem):
    """Enhanced multi-agent system with real-time progress tracking"""
    
    def __init__(self, user_id: str, thread_id: str = "default"):
        super().__init__(user_id, thread_id)
        self.session_id = None
    
    def set_session_id(self, session_id: str):
        """Set session ID for progress tracking"""
        self.session_id = session_id
    
    async def process_with_tracking(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """Process message with real-time workflow tracking"""
        
        self.set_session_id(session_id)
        start_time = datetime.now()
        
        # Initial state
        initial_state = {
            "user_message": user_message,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "messages": [],
            "memory_context": {},
            "selected_agent": "",
            "agent_response": "",
            "metadata": {},
            "tools_used": [],
            "wikipedia_results": [],
            "session_id": session_id  # Add session_id to state
        }
        
        try:
            # Execute workflow with tracking
            final_state = await self._execute_workflow_with_tracking(initial_state)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "response": final_state["agent_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": final_state["metadata"],
                "tools_used": final_state["tools_used"],
                "wikipedia_results": final_state["wikipedia_results"],
                "memory_context_summary": final_state["memory_context"].get("context_summary", ""),
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"💥 Enhanced Workflow error: {e}")
            await progress_tracker.update_step(session_id, "error", "error", f"Workflow failed: {str(e)}")
            
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "agent_used": "error",
                "metadata": {"error": str(e)},
                "tools_used": [],
                "wikipedia_results": [],
                "memory_context_summary": "",
                "processing_time_ms": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_workflow_with_tracking(self, initial_state: Dict) -> Dict:
        """Execute the workflow with step-by-step tracking"""
        
        session_id = initial_state["session_id"]
        
        # Step 1: Memory Fetch
        state = await self._tracked_memory_fetch(initial_state, session_id)
        
        # Step 2: Supervisor Decision
        state = await self._tracked_supervisor(state, session_id)
        
        # Step 3: Agent Processing
        if state["selected_agent"] == "rag_agent":
            state = await self._tracked_rag_agent(state, session_id)
        else:
            state = await self._tracked_chatbot_agent(state, session_id)
        
        # Step 4: Memory Update
        state = await self._tracked_memory_update(state, session_id)
        
        return state
    
    async def _tracked_memory_fetch(self, state: Dict, session_id: str) -> Dict:
        """Memory fetch with progress tracking"""
        await progress_tracker.update_step(session_id, "memory", "active", "Loading conversation context and user profile...")
        
        try:
            # Execute actual memory fetch
            result = enhanced_memory_fetch_node(state)
            
            # Extract context info for detailed progress
            memory_context = result.get("memory_context", {})
            details = []
            
            if memory_context.get("short_term"):
                details.append(f"{len(memory_context['short_term'])} recent messages")
            if memory_context.get("long_term"):
                details.append(f"{len(memory_context['long_term'])} relevant conversations")
            if memory_context.get("user_facts"):
                details.append(f"{len(memory_context['user_facts'])} user facts")
            
            detail_text = "Loaded: " + ", ".join(details) if details else "Memory context loaded"
            
            await progress_tracker.update_step(session_id, "memory", "completed", detail_text)
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "memory", "error", f"Memory fetch failed: {str(e)}")
            raise e
    
    async def _tracked_supervisor(self, state: Dict, session_id: str) -> Dict:
        """Supervisor with progress tracking"""
        await progress_tracker.update_step(session_id, "supervisor", "active", "Analyzing request intent and routing to appropriate agent...")
        
        try:
            result = enhanced_supervisor_node(state)
            selected_agent = result.get("selected_agent", "chatbot")
            
            agent_names = {
                "rag_agent": "RAG Agent (Document Search)",
                "chatbot": "Chatbot Agent (Conversation & Wikipedia)"
            }
            
            detail_text = f"Routed to: {agent_names.get(selected_agent, selected_agent)}"
            await progress_tracker.update_step(session_id, "supervisor", "completed", detail_text)
            
            # Send agent highlight
            session = progress_tracker.active_sessions.get(session_id)
            if session:
                websocket_manager = session["websocket_manager"]
                await websocket_manager.send_agent_highlight(session_id, selected_agent)
            
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "supervisor", "error", f"Supervisor routing failed: {str(e)}")
            raise e
    
    async def _tracked_rag_agent(self, state: Dict, session_id: str) -> Dict:
        """RAG agent with progress tracking"""
        await progress_tracker.update_step(session_id, "agent", "active", "Searching documents and knowledge base...")
        
        try:
            result = enhanced_rag_agent_node(state)
            
            # Extract RAG-specific details
            metadata = result.get("metadata", {})
            hits_count = metadata.get("hits_count", 0)
            sources = metadata.get("sources", [])
            
            detail_text = f"Found {hits_count} relevant documents"
            if sources:
                detail_text += f" from {len(set(sources))} sources"
            
            await progress_tracker.update_step(session_id, "agent", "completed", detail_text)
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "agent", "error", f"RAG agent failed: {str(e)}")
            raise e
    
    async def _tracked_chatbot_agent(self, state: Dict, session_id: str) -> Dict:
        """Chatbot agent with progress tracking"""
        await progress_tracker.update_step(session_id, "agent", "active", "Processing conversation with AI agent...")
        
        try:
            result = enhanced_chatbot_agent_node(state)
            
            # Extract chatbot-specific details
            tools_used = result.get("tools_used", [])
            wikipedia_results = result.get("wikipedia_results", [])
            
            details = ["Response generated"]
            if tools_used:
                details.append(f"Used tools: {', '.join(tools_used)}")
            if wikipedia_results:
                details.append(f"Wikipedia searches: {len(wikipedia_results)}")
            
            detail_text = " | ".join(details)
            await progress_tracker.update_step(session_id, "agent", "completed", detail_text)
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "agent", "error", f"Chatbot agent failed: {str(e)}")
            raise e
    
    async def _tracked_memory_update(self, state: Dict, session_id: str) -> Dict:
        """Memory update with progress tracking"""
        await progress_tracker.update_step(session_id, "update", "active", "Saving conversation to memory system...")
        
        try:
            result = enhanced_memory_update_node(state)
            
            # Check if memory was actually updated
            metadata = result.get("metadata", {})
            memory_updated = metadata.get("memory_updated", False)
            
            detail_text = "Conversation saved to memory" if memory_updated else "Memory update skipped"
            await progress_tracker.update_step(session_id, "update", "completed", detail_text)
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "update", "error", f"Memory update failed: {str(e)}")
            raise e

# ===============================
# Enhanced Connection Manager
# ===============================

class EnhancedConnectionManager:
    """Enhanced connection manager with workflow integration"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[session_id] = {
            "user_id": user_id,
            "connected_at": datetime.now().isoformat(),
            "message_count": 0,
            "tools_used": 0
        }
        
        # Register with progress tracker
        progress_tracker.register_session(session_id, self)
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "session_id": session_id,
            "message": "Connected to Multi-Agent AI System with real-time workflow tracking",
            "timestamp": datetime.now().isoformat()
        }, session_id)
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.user_sessions:
            del self.user_sessions[session_id]
        
        # Unregister from progress tracker
        progress_tracker.unregister_session(session_id)
    
    async def send_personal_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def send_workflow_update(self, session_id: str, step: str, status: str, details: str = None):
        """Send workflow step updates"""
        await self.send_personal_message({
            "type": "workflow_update",
            "step": step,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }, session_id)
    
    async def send_agent_highlight(self, session_id: str, agent_name: str):
        """Send agent highlighting update"""
        await self.send_personal_message({
            "type": "agent_highlight",
            "agent": agent_name,
            "timestamp": datetime.now().isoformat()
        }, session_id)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.user_sessions.get(session_id)

# ===============================
# Enhanced Multi-Agent Manager
# ===============================

class EnhancedMultiAgentManager:
    """Enhanced manager with real workflow integration"""
    
    def __init__(self):
        self.systems: Dict[str, EnhancedLangGraphMultiAgentSystem] = {}
        self.connection_manager = EnhancedConnectionManager()
    
    def get_or_create_system(self, user_id: str, thread_id: str = "default") -> EnhancedLangGraphMultiAgentSystem:
        """Get existing system or create new enhanced one"""
        system_key = f"{user_id}:{thread_id}"
        
        if system_key not in self.systems:
            # Create enhanced system instead of regular one
            base_system = create_langgraph_system(user_id=user_id, thread_id=thread_id)
            
            # Convert to enhanced system (copy attributes)
            enhanced_system = EnhancedLangGraphMultiAgentSystem(user_id=user_id, thread_id=thread_id)
            enhanced_system.workflow = base_system.workflow
            
            self.systems[system_key] = enhanced_system
            print(f"Created enhanced system for {system_key}")
        
        return self.systems[system_key]
    
    async def process_with_real_workflow(
        self, 
        system: EnhancedLangGraphMultiAgentSystem, 
        message: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """Process message using real workflow with tracking"""
        
        try:
            # Use the enhanced processing method
            result = await system.process_with_tracking(message, session_id)
            
            # Update session stats
            if session_id in self.connection_manager.user_sessions:
                session = self.connection_manager.user_sessions[session_id]
                session["message_count"] += 1
                session["tools_used"] += len(result.get("tools_used", []))
            
            return result
            
        except Exception as e:
            await progress_tracker.update_step(session_id, "error", "error", f"Processing failed: {str(e)}")
            raise e

# ===============================
# FastAPI Application Setup
# ===============================

# Global enhanced manager
enhanced_agent_manager = EnhancedMultiAgentManager()
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    print("🚀 Starting Enhanced Multi-Agent AI System...")
    
    try:
        # Test enhanced system creation
        test_system = enhanced_agent_manager.get_or_create_system("system_test", "health_check")
        print("✅ Enhanced multi-agent system initialized successfully")
        print("📊 Real-time workflow tracking enabled")
    except Exception as e:
        print(f"⚠️ Warning: Enhanced system initialization failed: {e}")
    
    yield
    
    print("🔄 Shutting down Enhanced Multi-Agent AI System...")

# Create FastAPI app
app = FastAPI(
    title="Enhanced Multi-Agent AI System",
    description="Professional AI system with real-time LangGraph workflow tracking",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# Authentication
# ===============================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Optional authentication"""
    if credentials is None:
        return {"user_id": "anonymous", "is_authenticated": False}
    
    try:
        user_id = credentials.credentials or "anonymous"
        return {"user_id": user_id, "is_authenticated": True}
    except Exception:
        return {"user_id": "anonymous", "is_authenticated": False}

# ===============================
# Enhanced API Endpoints
# ===============================

@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check with workflow status"""
    try:
        # Test workflow components
        workflow_status = {
            "memory_fetch": "available",
            "supervisor": "available", 
            "rag_agent": "checking...",
            "chatbot_agent": "available",
            "memory_update": "available"
        }
        
        # Test memory system
        try:
            from memory.mem_agent import MemoryAgent
            from memory.mem_config import MemoryConfig
            workflow_status["memory_system"] = "available"
        except ImportError:
            workflow_status["memory_system"] = "mock_system"
        
        # Test RAG system
        try:
            from rag_agent.ragagent import RagAgent, rag_answer
            workflow_status["rag_agent"] = "available"
        except ImportError:
            workflow_status["rag_agent"] = "unavailable"
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "workflow_tracking": "enabled",
            "active_sessions": len(progress_tracker.active_sessions),
            "workflow_status": workflow_status,
            "agents_available": ["supervisor", "chatbot", "rag_agent", "memory"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced health check failed: {str(e)}")

@app.post("/api/chat")
async def enhanced_chat_endpoint(request: dict, current_user: dict = Depends(get_current_user)):
    """Enhanced REST endpoint with workflow tracking"""
    try:
        user_message = request.get("message", "")
        user_id = request.get("user_id", current_user["user_id"])
        thread_id = request.get("thread_id", "default")
        
        # Generate session ID for tracking
        session_id = f"rest_{uuid.uuid4().hex[:8]}"
        
        # Get or create enhanced system
        system = enhanced_agent_manager.get_or_create_system(user_id=user_id, thread_id=thread_id)
        
        # Process with real workflow tracking
        result = await enhanced_agent_manager.process_with_real_workflow(system, user_message, session_id)
        
        return result
    
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced chat processing failed: {str(e)}")

# ===============================
# Enhanced WebSocket Endpoint
# ===============================

@app.websocket("/ws/{session_id}")
async def enhanced_websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str = "anonymous"):
    """Enhanced WebSocket with real workflow tracking"""
    await enhanced_agent_manager.connection_manager.connect(websocket, session_id, user_id)
    
    # Get or create enhanced AI system
    system = enhanced_agent_manager.get_or_create_system(user_id=user_id, thread_id=session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                user_message = message_data.get("message", "")
                
                if user_message.strip():
                    try:
                        # Process message with REAL workflow tracking
                        result = await enhanced_agent_manager.process_with_real_workflow(
                            system, user_message, session_id
                        )
                        
                        # Send response back to client
                        await enhanced_agent_manager.connection_manager.send_personal_message({
                            "type": "chat_response",
                            "response": result["response"],
                            "agent_used": result["agent_used"],
                            "tools_used": result["tools_used"],
                            "wikipedia_results": result["wikipedia_results"],
                            "metadata": result["metadata"],
                            "memory_context_summary": result["memory_context_summary"],
                            "processing_time_ms": result["processing_time_ms"],
                            "timestamp": result["timestamp"]
                        }, session_id)
                        
                        # Send metrics update
                        session_info = enhanced_agent_manager.connection_manager.get_session_info(session_id)
                        if session_info:
                            await enhanced_agent_manager.connection_manager.send_personal_message({
                                "type": "metrics_update",
                                "message_count": session_info["message_count"],
                                "tools_used": session_info["tools_used"]
                            }, session_id)
                        
                    except Exception as e:
                        await enhanced_agent_manager.connection_manager.send_personal_message({
                            "type": "error",
                            "message": f"Processing failed: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        }, session_id)
            
            elif message_data.get("type") == "ping":
                await enhanced_agent_manager.connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, session_id)
                
    except WebSocketDisconnect:
        enhanced_agent_manager.connection_manager.disconnect(session_id)
        print(f"Enhanced client {session_id} disconnected")
    except Exception as e:
        print(f"Enhanced WebSocket error for {session_id}: {e}")
        enhanced_agent_manager.connection_manager.disconnect(session_id)

# ===============================
# Dashboard Routes
# ===============================

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_enhanced_dashboard():
    """Serve the enhanced dashboard"""
    try:
        return FileResponse("static/index.html")
    except FileNotFoundError:
        return HTMLResponse("""
        <h1>Enhanced Multi-Agent AI System</h1>
        <p>✅ Backend is running with REAL workflow tracking!</p>
        <p>📋 Save the integrated dashboard as static/index.html</p>
        <p>🔗 WebSocket: ws://localhost:8000/ws/{{session_id}}</p>
        <p>📊 Active sessions: {}</p>
        """.format(len(progress_tracker.active_sessions)))

@app.get("/api/workflow/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get current workflow status for a session"""
    if session_id not in progress_tracker.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = progress_tracker.active_sessions[session_id]
    return {
        "session_id": session_id,
        "current_step": session.get("current_step"),
        "steps_completed": session.get("steps_completed", []),
        "start_time": session.get("start_time"),
        "active": True
    }

# ===============================
# Static Files
# ===============================

# Uncomment when you have the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===============================
# Main Application Runner
# ===============================

if __name__ == "__main__":
    print("🚀 Starting Enhanced Multi-Agent AI System with REAL Workflow Tracking...")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("🔌 WebSocket: ws://localhost:8000/ws/{session_id}")
    print("⚡ API docs: http://localhost:8000/docs")
    print("🎯 Real-time workflow progress enabled!")
    
    uvicorn.run(
        "main_old:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )