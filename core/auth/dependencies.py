"""
FastAPI authentication dependencies
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, Cookie

from core.config import Config
from core.auth.jwt_handler import verify_jwt_token


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None, alias=Config.COOKIE_NAME)
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