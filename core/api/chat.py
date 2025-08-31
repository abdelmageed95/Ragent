"""
Chat API routes
"""
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException

from models.models import ChatMessage, UserResponse
from core.auth.dependencies import require_auth

router = APIRouter(prefix="/api")


@router.get("/me")
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


@router.post("/chat")
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