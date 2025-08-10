"""
Complete Multi-Agent AI System with Authentication and MongoDB
Includes: Registration, Login, Session Management, and Multi-Page Support
"""

import os
import json
import secrets
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import bcrypt
import motor.motor_asyncio
from bson import ObjectId

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Cookie, Request, Response, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, EmailStr
import uvicorn
import jwt

# Import the enhanced LangGraph system
try:
    from graph.workflow import (
        EnhancedLangGraphMultiAgentSystem,
        create_enhanced_langgraph_system
    )
    print("✅ Enhanced LangGraph system imported successfully")
except ImportError as e:
    print(f"❌ Failed to import enhanced LangGraph system: {e}")
    exit(1)

# ===============================
# Configuration
# ===============================

# JWT Configuration - Must set JWT_SECRET in production
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    print("⚠️ WARNING: JWT_SECRET not set. Using random secret (sessions will not persist across restarts)")
    JWT_SECRET = secrets.token_urlsafe(32)
    print(f"🔑 Generated JWT secret length: {len(JWT_SECRET)}")
else:
    print(f"🔑 Using environment JWT secret length: {len(JWT_SECRET)}")
JWT_ALGORITHM = "HS256"
SESSION_EXPIRE_HOURS = 24 * 7  # 7 days
COOKIE_NAME = "ai_system_session"

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "agentic_memory"

# Security Configuration
IS_PRODUCTION = False #os.getenv("ENVIRONMENT", "production").lower() == "production"
COOKIE_SECURE = IS_PRODUCTION  # Only send cookies over HTTPS in production
print(f"🔧 Environment: {'production' if IS_PRODUCTION else 'development'}, Cookie secure: {COOKIE_SECURE}")

# ===============================
# Database Models
# ===============================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    last_active: datetime
    session_count: int
    total_messages: int
    is_active: bool

class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class SessionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class SessionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    last_active: datetime
    message_count: int
    tools_used: int
    is_active: bool

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None

# ===============================
# MongoDB Database Manager
# ===============================

class DatabaseManager:
    """MongoDB database manager for users and sessions"""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.db = self.client[database_name]
        self.users = self.db.users
        self.sessions = self.db.sessions
        self.messages = self.db.messages
        
    async def init_database(self):
        """Initialize database with indexes"""
        try:
            # Create indexes
            await self.users.create_index("email", unique=True)
            await self.users.create_index("username", unique=True)
            await self.sessions.create_index([("user_id", 1), ("created_at", -1)])
            await self.messages.create_index([("session_id", 1), ("created_at", 1)])
            
            print("✅ MongoDB database initialized with indexes")
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")
    
    # User Management
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Create a new user"""
        print(f"🔍 Creating user: {user_data.email}")
        # Hash password
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
        
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "session_count": 0,
            "total_messages": 0,
            "is_active": True
        }
        
        try:
            result = await self.users.insert_one(user_doc)
            user_doc["_id"] = result.inserted_id
            print(f"✅ User created successfully: {user_data.email}")
            return user_doc
        except Exception as e:
            print(f"❌ User creation failed: {e}")
            if "email" in str(e):
                raise HTTPException(status_code=400, detail="Email already registered")
            elif "username" in str(e):
                raise HTTPException(status_code=400, detail="Username already taken")
            else:
                raise HTTPException(status_code=500, detail="Failed to create user")
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user login"""
        print(f"🔍 Attempting to authenticate user: {email}")
        user = await self.users.find_one({"email": email, "is_active": True})
        if not user:
            print(f"❌ User not found: {email}")
            return None
        
        print(f"✅ User found: {email}")
        if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
            print(f"✅ Password valid for user: {email}")
            # Update last active
            await self.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_active": datetime.now()}}
            )
            return user
        else:
            print(f"❌ Invalid password for user: {email}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            return await self.users.find_one({"_id": ObjectId(user_id), "is_active": True})
        except:
            return None
    
    async def update_user_activity(self, user_id: str, message_count_delta: int = 0):
        """Update user activity"""
        try:
            await self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {"last_active": datetime.now()},
                    "$inc": {"total_messages": message_count_delta}
                }
            )
        except Exception as e:
            print(f"Failed to update user activity: {e}")
    
    # Session Management
    async def create_session(self, user_id: str, session_data: SessionCreate) -> Dict[str, Any]:
        """Create a new session for user"""
        session_doc = {
            "user_id": ObjectId(user_id),
            "name": session_data.name,
            "description": session_data.description,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "message_count": 0,
            "tools_used": 0,
            "is_active": True
        }
        
        result = await self.sessions.insert_one(session_doc)
        session_doc["_id"] = result.inserted_id
        
        # Update user session count
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"session_count": 1}}
        )
        
        return session_doc
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            cursor = self.sessions.find(
                {"user_id": ObjectId(user_id), "is_active": True}
            ).sort("last_active", -1)
            return await cursor.to_list(length=None)
        except:
            return []
    
    async def get_session_by_id(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID (with user verification)"""
        try:
            return await self.sessions.find_one({
                "_id": ObjectId(session_id),
                "user_id": ObjectId(user_id),
                "is_active": True
            })
        except:
            return None
    
    async def update_session_activity(self, session_id: str, message_count_delta: int = 0, tools_used_delta: int = 0):
        """Update session activity"""
        try:
            await self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {"last_active": datetime.now()},
                    "$inc": {
                        "message_count": message_count_delta,
                        "tools_used": tools_used_delta
                    }
                }
            )
        except Exception as e:
            print(f"Failed to update session activity: {e}")
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session"""
        try:
            result = await self.sessions.update_one(
                {"_id": ObjectId(session_id), "user_id": ObjectId(user_id)},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except:
            return False
    
    async def rename_session(self, session_id: str, user_id: str, new_name: str, new_description: Optional[str] = None) -> bool:
        """Rename a session"""
        try:
            update_data = {"name": new_name}
            if new_description is not None:
                update_data["description"] = new_description
            
            result = await self.sessions.update_one(
                {"_id": ObjectId(session_id), "user_id": ObjectId(user_id), "is_active": True},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            return False
    
    # Message Management
    async def save_message(self, session_id: str, user_message: str, ai_response: str, metadata: Dict[str, Any]):
        """Save chat message"""
        try:
            message_doc = {
                "session_id": ObjectId(session_id),
                "user_message": user_message,
                "ai_response": ai_response,
                "metadata": metadata,
                "created_at": datetime.now()
            }
            await self.messages.insert_one(message_doc)
        except Exception as e:
            print(f"Failed to save message: {e}")
    
    async def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        try:
            cursor = self.messages.find(
                {"session_id": ObjectId(session_id)}
            ).sort("created_at", 1).limit(limit)
            return await cursor.to_list(length=None)
        except:
            return []

# ===============================
# Authentication Utilities
# ===============================

def create_jwt_token(user_id: str) -> str:
    """Create JWT token for user"""
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT configuration error")
    
    import time
    current_time = int(time.time())
    payload = {
        "user_id": user_id,
        "exp": current_time + (SESSION_EXPIRE_HOURS * 3600),
        "iat": current_time - 60  # Set 1 minute in past for safety
    }
    print(f"🔑 Creating JWT with secret length: {len(JWT_SECRET)}")
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(f"✅ JWT token created with iat: {payload['iat']}, current: {current_time}")
    return token

def verify_jwt_token(token: str) -> Optional[Dict[str, str]]:
    """Verify JWT token and return payload"""
    if not JWT_SECRET:
        print("❌ JWT secret not configured")
        return None
        
    try:
        print(f"🔑 Verifying JWT with secret length: {len(JWT_SECRET)}")
        print(f"🔑 JWT token to verify: {token}")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        print("✅ JWT token verified successfully")
        return payload
    except jwt.ExpiredSignatureError:
        print("❌ JWT token expired")
        return None

    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid JWT token: {e}")
        return None

# ===============================
# Authentication Dependencies
# ===============================

async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None, alias=COOKIE_NAME)
) -> Optional[Dict[str, Any]]:
    """Get current authenticated user"""
    print(f"🔍 Checking authentication - Cookie: {session_token is not None}")
    if not session_token:
        print("❌ No session token found")
        return None
    print("🔍 Verifying JWT token")
    payload = verify_jwt_token(session_token)
    if not payload:
        print("❌ Invalid JWT token")
        return None

    user_id = payload.get("user_id")
    if not user_id:
        print("❌ No user_id in JWT payload")
        return None

    print(f"🔍 Looking up user: {user_id}")
    db = request.app.state.db
    user = await db.get_user_by_id(user_id)
    if user:
        print(f"✅ User authenticated: {user['email']}")
        # Update last active
        await db.update_user_activity(user_id)
    else:
        print(f"❌ User not found: {user_id}")

    return user

async def require_auth(current_user: Optional[Dict] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

# ===============================
# Multi-Agent Manager with Database
# ===============================

class DatabaseAwareMultiAgentManager:
    """Multi-agent manager with database integration and performance optimizations"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.langgraph_systems: Dict[str, EnhancedLangGraphMultiAgentSystem] = {}
        self.memory_agents: Dict[str, Any] = {}  # Cache memory agents
        self.active_websockets: Dict[str, WebSocket] = {}
    
    def get_or_create_system(self, user_id: str, session_id: str) -> EnhancedLangGraphMultiAgentSystem:
        """Get or create LangGraph system for user session"""
        system_key = f"{user_id}:{session_id}"
        
        if system_key not in self.langgraph_systems:
            self.langgraph_systems[system_key] = create_enhanced_langgraph_system(
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
                message, session_id, websocket_callback, chat_mode
            )
            
            # Update database
            tools_used = len(result.get("tools_used", []))
            await self.db.update_session_activity(
                session_id, 
                message_count_delta=1,
                tools_used_delta=tools_used
            )
            await self.db.update_user_activity(user_id, message_count_delta=1)
            
            # Save message to database
            await self.db.save_message(
                session_id=session_id,
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

# ===============================
# FastAPI Application Setup
# ===============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with database setup"""
    print("🚀 Starting Multi-Agent AI System with MongoDB Authentication...")
    
    # Initialize database
    db = DatabaseManager(MONGODB_URL, DATABASE_NAME)
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

# CORS middleware - Secure configuration
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://localhost:8000",
    "https://127.0.0.1:8000",
]

# Add production origins from environment variable
if prod_origins := os.getenv("ALLOWED_ORIGINS"):
    ALLOWED_ORIGINS.extend(prod_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Only necessary methods
    allow_headers=["Accept", "Accept-Language", "Content-Type", "Authorization"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# ===============================
# Authentication Routes
# ===============================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: Optional[Dict] = Depends(get_current_user)):
    """Home page - redirect based on authentication"""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    else:
        return RedirectResponse(url="/login", status_code=302)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    try:
        return templates.TemplateResponse("register.html", {"request": request})
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_register_html())

@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None)
):
    """Register new user"""
    try:
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            full_name=full_name if full_name else None
        )
        
        db = request.app.state.db
        user = await db.create_user(user_data)
        
        # Create JWT token
        token = create_jwt_token(str(user["_id"]))
        print(f"✅ Registration: Created JWT token for user: {user['email']}")
        
        # Redirect to dashboard with cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=SESSION_EXPIRE_HOURS * 3600,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="strict" if IS_PRODUCTION else "lax"
        )
        print(f"🍪 Registration: Set cookie - Name: {COOKIE_NAME}, Secure: {COOKIE_SECURE}, Production: {IS_PRODUCTION}")
        
        return response
        
    except HTTPException as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": e.detail
        }, status_code=e.status_code)
    except Exception as e:
        print(f"Registration error: {e}")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Registration failed. Please try again."
        }, status_code=500)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_login_html())

@app.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Login user"""
    try:
        db = request.app.state.db
        user = await db.authenticate_user(email, password)
        
        if not user:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid email or password"
            }, status_code=401)
        
        # Create JWT token
        token = create_jwt_token(str(user["_id"]))
        print(f"✅ Login: Created JWT token for user: {user['email']}")
        
        # Redirect to dashboard with cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=SESSION_EXPIRE_HOURS * 3600,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="strict" if IS_PRODUCTION else "lax"
        )
        print(f"🍪 Login: Set cookie - Name: {COOKIE_NAME}, Secure: {COOKIE_SECURE}, Production: {IS_PRODUCTION}")
        
        return response
        
    except Exception as e:
        print(f"Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Login failed. Please try again."
        }, status_code=500)

@app.post("/logout")
async def logout_user():
    """Logout user"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=COOKIE_NAME)
    return response

# ===============================
# Dashboard and Session Routes
# ===============================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: Dict = Depends(require_auth)
):
    """Dashboard with session selection"""
    try:
        db = request.app.state.db
        sessions = await db.get_user_sessions(str(current_user["_id"]))
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "sessions": sessions,
            "now": datetime.now  # Pass as function, not called
        })
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_dashboard_html(current_user))

@app.get("/chat/{session_id}", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    session_id: str,
    current_user: Dict = Depends(require_auth)
):
    """Chat interface for specific session"""
    try:
        db = request.app.state.db
        session = await db.get_session_by_id(session_id, str(current_user["_id"]))
        
        if not session:
            return RedirectResponse(url="/dashboard", status_code=302)
        
        # Get recent messages
        messages = await db.get_session_messages(session_id, limit=50)
        
        # Create a temporary auth token for WebSocket (since HTTP-only cookies can't be accessed by JS)
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
# API Routes
# ===============================

@app.get("/api/me")
async def get_current_user_info(current_user: Dict = Depends(require_auth)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user["_id"]),
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        created_at=current_user["created_at"],
        last_active=current_user["last_active"],
        session_count=current_user["session_count"],
        total_messages=current_user["total_messages"],
        is_active=current_user["is_active"]
    )

@app.get("/api/sessions")
async def get_user_sessions(
    request: Request,
    current_user: Dict = Depends(require_auth)
):
    """Get all sessions for current user"""
    db = request.app.state.db
    sessions = await db.get_user_sessions(str(current_user["_id"]))
    
    return {
        "sessions": [
            SessionResponse(
                id=str(session["_id"]),
                name=session["name"],
                description=session.get("description"),
                created_at=session["created_at"],
                last_active=session["last_active"],
                message_count=session["message_count"],
                tools_used=session["tools_used"],
                is_active=session["is_active"]
            )
            for session in sessions
        ]
    }

@app.post("/api/sessions")
async def create_new_session(
    request: Request,
    session_data: SessionCreate,
    current_user: Dict = Depends(require_auth)
):
    """Create new session"""
    try:
        print(f"🔄 Creating session for user: {current_user['email']}")
        print(f"📝 Session data: {session_data.dict()}")
        db = request.app.state.db
        session = await db.create_session(str(current_user["_id"]), session_data)
        print(f"✅ Session created: {session['_id']}")
        
        return {
            "id": str(session["_id"]),
            "name": session["name"],
            "description": session.get("description"),
            "created_at": session["created_at"]
        }
    except Exception as e:
        print(f"❌ Session creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.delete("/api/sessions/{session_id}")
async def delete_session(
    request: Request,
    session_id: str,
    current_user: Dict = Depends(require_auth)
):
    """Delete session"""
    db = request.app.state.db
    success = await db.delete_session(session_id, str(current_user["_id"]))
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

@app.put("/api/sessions/{session_id}")
async def rename_session(
    request: Request,
    session_id: str,
    session_data: SessionUpdate,
    current_user: Dict = Depends(require_auth)
):
    """Rename/update session"""
    db = request.app.state.db
    success = await db.rename_session(
        session_id, 
        str(current_user["_id"]), 
        session_data.name,
        session_data.description
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session updated successfully"}

@app.post("/api/chat")
async def chat_endpoint(
    request: Request,
    message_data: ChatMessage,
    current_user: Dict = Depends(require_auth)
):
    """Chat endpoint with authentication"""
    if not message_data.session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # Verify session belongs to user
    db = request.app.state.db
    session = await db.get_session_by_id(message_data.session_id, str(current_user["_id"]))
    if not session:
        raise HTTPException(status_code=403, detail="Session not accessible")
    
    try:
        # Process with multi-agent manager
        result = await request.app.state.multi_agent_manager.process_message(
            message_data.message,
            str(current_user["_id"]),
            message_data.session_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

# ===============================
# WebSocket with Authentication
# ===============================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket with authentication"""
    print(f"🔌 WebSocket connection attempt for session: {session_id}")
    await websocket.accept()
    print("✅ WebSocket accepted")
    websocket_key = None  # Initialize to prevent unbound variable
    
    try:
        # Get authentication from first message
        print("🔍 Waiting for auth message...")
        auth_data = await websocket.receive_text()
        print(f"📨 Received auth data: {auth_data}")
        auth_message = json.loads(auth_data)
        print(f"📋 Parsed auth message: {auth_message}")
        
        token = auth_message.get("auth_token")
        if not token:
            print("❌ No auth token in message")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication required"
            }))
            await websocket.close()
            return
        
        print(f"🔑 Got auth token: {token[:20]}...")
        
        # Verify token
        print("🔍 Verifying JWT token...")
        payload = verify_jwt_token(token)
        if not payload:
            print("❌ JWT token verification failed")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid or expired token"
            }))
            await websocket.close()
            return
        
        print(f"✅ JWT verified, payload: {payload}")
        user_id = payload["user_id"]
        print(f"👤 User ID from token: {user_id}")
        
        # Verify session access
        print(f"🔍 Checking session access for session {session_id}, user {user_id}")
        db = app.state.db
        session = await db.get_session_by_id(session_id, user_id)
        if not session:
            print(f"❌ Session {session_id} not accessible for user {user_id}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Session not accessible"
            }))
            await websocket.close()
            return
        
        print(f"✅ Session verified: {session.get('name', 'Unknown')}")
        
        # Register WebSocket with unique key to prevent collisions
        websocket_key = f"{user_id}:{session_id}"
        app.state.multi_agent_manager.active_websockets[websocket_key] = websocket
        
        # Send connection confirmation
        print("✅ Sending connection confirmation...")
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "user_id": user_id,
            "message": "Connected with authentication"
        }))
        print("✅ WebSocket fully connected and ready")
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                user_message = message_data.get("message", "")
                chat_mode = message_data.get("mode", "general")  # Default to general
                
                if user_message.strip():
                    try:
                        result = await app.state.multi_agent_manager.process_message(
                            user_message, user_id, session_id, chat_mode
                        )
                        
                        print(f"🔍 Sending WebSocket response with result keys: {list(result.keys())}")
                        print(f"🔍 Agent type in result: {result.get('agent_type', 'NOT FOUND')}")
                        print(f"🔍 Selected agent in result: {result.get('selected_agent', 'NOT FOUND')}")  
                        print(f"🔍 Metadata in result: {result.get('metadata', {})}")
                        print(f"🔍 Chat mode used: {chat_mode}")
                        
                        response_data = {
                            "type": "chat_response",
                            **result
                        }
                        print(f"🔍 Final response data keys: {list(response_data.keys())}")
                        print(f"🔍 Final agent_type: {response_data.get('agent_type', 'NOT FOUND')}")
                        
                        await websocket.send_text(json.dumps(response_data))
                        
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Processing failed: {str(e)}"
                        }))
            
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected normally: {session_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {type(e).__name__}: {e}")
        print(f"📍 Error occurred at session: {session_id}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print(f"🧹 Cleaning up WebSocket for session: {session_id}")
        if websocket_key and websocket_key in app.state.multi_agent_manager.active_websockets:
            del app.state.multi_agent_manager.active_websockets[websocket_key]
            print(f"✅ WebSocket cleaned up: {websocket_key}")
        else:
            print(f"⚠️ No WebSocket key to clean up: {websocket_key}")

# ===============================
# Health Check
# ===============================

@app.get("/health")
async def health_check():
    """Health check with database status"""
    try:
        # Test database connection
        db = app.state.db
        await db.users.find_one({})
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "version": "4.0.0",
        "authentication": "enabled",
        "database": db_status,
        "session_management": "mongodb",
        "timestamp": datetime.now().isoformat()
    }

# ===============================
# Fallback HTML Templates
# ===============================

def get_register_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Register - AI System</title></head>
    <body>
        <h1>Register</h1>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="email" type="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <input name="full_name" placeholder="Full Name">
            <button type="submit">Register</button>
        </form>
        <a href="/login">Already have an account? Login</a>
    </body>
    </html>
    """

def get_login_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Login - AI System</title></head>
    <body>
        <h1>Login</h1>
        <form method="post">
            <input name="email" type="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <a href="/register">Don't have an account? Register</a>
    </body>
    </html>
    """

def get_dashboard_html(user):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard - AI System</title></head>
    <body>
        <h1>Welcome, {user['username']}!</h1>
        <p>MongoDB backend is running. Save templates to templates/ directory for full UI.</p>
        <form method="post" action="/logout">
            <button type="submit">Logout</button>
        </form>
    </body>
    </html>
    """

def get_chat_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Chat - AI System</title></head>
    <body>
        <h1>Chat Interface</h1>
        <p>MongoDB backend is running. Save templates to templates/ directory for full UI.</p>
        <a href="/dashboard">Back to Dashboard</a>
    </body>
    </html>
    """

# ===============================
# Static Files
# ===============================

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass

# ===============================
# Main Application Runner
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
