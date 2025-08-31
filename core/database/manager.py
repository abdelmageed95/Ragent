"""
MongoDB database manager for users and sessions
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import motor.motor_asyncio
from bson import ObjectId
from fastapi import HTTPException

from models.models import UserCreate, SessionCreate
from core.auth.utils import hash_password, verify_password


class DatabaseManager:
    """MongoDB database manager for users and sessions"""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.db = self.client[database_name]
        self.users = self.db.users
        self.sessions = self.db.sessions
        self.conversations = self.db.conversations  # Unified collection
        
    async def init_database(self):
        """Initialize database with indexes"""
        try:
            # Create indexes
            await self.users.create_index("email", unique=True)
            await self.users.create_index("username", unique=True)
            await self.sessions.create_index([("user_id", 1), ("created_at", -1)])
            await self.conversations.create_index([("session_id", 1), ("timestamp", 1)])
            await self.conversations.create_index([("user_id", 1), ("thread_id", 1), ("timestamp", 1)])
            
            print("✅ MongoDB database initialized with indexes")
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")
    
    # User Management
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Create a new user"""
        print(f"🔍 Creating user: {user_data.email}")
        # Hash password
        password_hash = hash_password(user_data.password)
        
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
        if verify_password(password, user["password_hash"]):
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
    
    # Conversation Management (Unified)
    async def save_conversation_messages(self, session_id: str, user_id: str, thread_id: str, 
                                       user_message: str, ai_response: str, metadata: Dict[str, Any]):
        """Save conversation messages in unified collection"""
        try:
            import uuid
            message_pair_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Handle ObjectId conversion safely
            try:
                session_obj_id = ObjectId(session_id) if len(session_id) == 24 else session_id
                user_obj_id = ObjectId(user_id) if len(user_id) == 24 else user_id
            except:
                session_obj_id = session_id
                user_obj_id = user_id
            
            messages = [
                {
                    "session_id": session_obj_id,
                    "thread_id": thread_id,
                    "user_id": user_obj_id,
                    "role": "user",
                    "content": user_message,
                    "metadata": {},
                    "timestamp": timestamp,
                    "message_pair_id": message_pair_id
                },
                {
                    "session_id": session_obj_id,
                    "thread_id": thread_id,
                    "user_id": user_obj_id,
                    "role": "assistant",
                    "content": ai_response,
                    "metadata": metadata,
                    "timestamp": timestamp,
                    "message_pair_id": message_pair_id
                }
            ]
            
            await self.conversations.insert_many(messages)
        except Exception as e:
            print(f"Failed to save conversation messages: {e}")
    
    async def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a session (UI format)"""
        try:
            # Handle ObjectId conversion safely
            try:
                session_obj_id = ObjectId(session_id) if len(session_id) == 24 else session_id
            except:
                session_obj_id = session_id
                
            cursor = self.conversations.find(
                {"session_id": session_obj_id}
            ).sort("timestamp", 1).limit(limit * 2)  # *2 because we have user+assistant pairs
            
            messages = await cursor.to_list(length=None)
            
            # Group messages by message_pair_id for UI
            grouped = {}
            for msg in messages:
                pair_id = msg.get("message_pair_id")
                if pair_id not in grouped:
                    grouped[pair_id] = {"user_message": "", "ai_response": "", "metadata": {}, "created_at": msg["timestamp"]}
                
                if msg["role"] == "user":
                    grouped[pair_id]["user_message"] = msg["content"]
                elif msg["role"] == "assistant":
                    grouped[pair_id]["ai_response"] = msg["content"]
                    grouped[pair_id]["metadata"] = msg["metadata"]
            
            return list(grouped.values())[:limit]
        except Exception as e:
            print(f"Error getting session messages: {e}")
            return []