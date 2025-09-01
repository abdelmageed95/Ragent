"""
Agentic RAG - Multi-Agent AI System
Professional modular application structure
"""
import os
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

# Core imports
from core.config import Config
from core.database.manager import DatabaseManager
from core.websocket.manager import DatabaseAwareMultiAgentManager
from core.websocket.handler import handle_websocket_connection
from core.auth.dependencies import get_current_user
from core.templates.fallbacks import get_dashboard_html, get_chat_html
from core.auth.jwt_handler import create_jwt_token

# API route imports
from core.api.auth import router as auth_router
from core.api.sessions import router as sessions_router
from core.api.chat import router as chat_router
from core.api.health import router as health_router
from core.api.knowledge_base import router as kb_router

# Graph system import
try:
    from graph.workflow import create_enhanced_langgraph_system
    print("✅ Enhanced LangGraph system imported successfully")
except ImportError as e:
    print(f"❌ Failed to import enhanced LangGraph system: {e}")
    exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with database setup"""
    print("🚀 Starting Multi-Agent AI System with MongoDB Authentication...")
    Config.print_config()
    
    # Initialize database
    db = DatabaseManager(Config.MONGODB_URL, Config.DATABASE_NAME)
    await db.init_database()
    app.state.db = db
    
    # Initialize multi-agent manager
    app.state.multi_agent_manager = DatabaseAwareMultiAgentManager(db)
    
    print("✅ Authentication system initialized with MongoDB")
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'db'):
        app.state.db.client.close()
    print("🔄 Shutting down with database cleanup...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent AI System with Authentication",
    description="Professional AI system with user authentication and session management",
    version="4.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Accept-Language", "Content-Type", "Authorization"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(kb_router)


# ===============================
# Main Navigation Routes
# ===============================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user = Depends(get_current_user)):
    """Home page - redirect based on authentication"""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    else:
        return RedirectResponse(url="/login", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user = Depends(get_current_user)):
    """Dashboard with session selection"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        db = request.app.state.db
        sessions = await db.get_user_sessions(str(current_user["_id"]))
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "sessions": sessions,
            "now": datetime.now
        })
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_dashboard_html(current_user))


@app.get("/chat/{session_id}", response_class=HTMLResponse)
async def chat_page(request: Request, session_id: str, current_user = Depends(get_current_user)):
    """Chat interface for specific session"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        db = request.app.state.db
        session = await db.get_session_by_id(session_id, str(current_user["_id"]))
        
        if not session:
            return RedirectResponse(url="/dashboard", status_code=302)
        
        # Get recent messages
        messages = await db.get_session_messages(session_id, limit=50)
        
        # Create a temporary auth token for WebSocket
        ws_auth_token = create_jwt_token(str(current_user["_id"]))
        
        return templates.TemplateResponse("chat.html", {
            "request": request,
            "user": current_user,
            "session": session,
            "messages": messages,
            "ws_auth_token": ws_auth_token
        })
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_chat_html())


# ===============================
# WebSocket Route
# ===============================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket with authentication"""
    await handle_websocket_connection(websocket, session_id, app)


# ===============================
# Static Files
# ===============================

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


# ===============================
# Application Runner
# ===============================

if __name__ == "__main__":
    print("🚀 Starting Multi-Agent AI System with MongoDB Authentication...")
    print("=" * 70)
    print("🔐 Features:")
    print("  - User registration and login")
    print("  - MongoDB data storage")
    print("  - JWT authentication")
    print("  - Session management")
    print("  - Multi-page interface")
    print("  - Real-time WebSocket with auth")
    print("=" * 70)
    
    # Environment check
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ WARNING: OPENAI_API_KEY not set")
    if not os.getenv("MONGODB_URL"):
        print("⚠️ INFO: Using default MongoDB URL (mongodb://localhost:27017)")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )