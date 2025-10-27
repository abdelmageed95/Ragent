"""
Session management API routes
"""
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException

from models.models import SessionCreate, SessionUpdate, SessionResponse
from core.auth.dependencies import require_auth

router = APIRouter(prefix="/api")


@router.get("/sessions")
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
                session_type=session.get("session_type", "ai"),
                created_at=session["created_at"],
                last_active=session["last_active"],
                message_count=session["message_count"],
                tools_used=session["tools_used"],
                is_active=session["is_active"]
            )
            for session in sessions
        ]
    }


@router.post("/sessions")
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


@router.delete("/sessions/{session_id}")
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


@router.put("/sessions/{session_id}")
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