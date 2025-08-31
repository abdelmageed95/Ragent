"""
JWT token handling utilities
"""
import time
from typing import Optional, Dict
import jwt
from fastapi import HTTPException

from core.config import Config


def create_jwt_token(user_id: str) -> str:
    """Create JWT token for user"""
    if not Config.JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT configuration error")
    
    current_time = int(time.time())
    payload = {
        "user_id": user_id,
        "exp": current_time + (Config.SESSION_EXPIRE_HOURS * 3600),
        "iat": current_time - 60  # Set 1 minute in past for safety
    }
    print(f"🔑 Creating JWT with secret length: {len(Config.JWT_SECRET)}")
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    print(f"✅ JWT token created with iat: {payload['iat']}, current: {current_time}")
    return token


def verify_jwt_token(token: str) -> Optional[Dict[str, str]]:
    """Verify JWT token and return payload"""
    if not Config.JWT_SECRET:
        print("❌ JWT secret not configured")
        return None
        
    try:
        print(f"🔑 Verifying JWT with secret length: {len(Config.JWT_SECRET)}")
        print(f"🔑 JWT token to verify: {token}")
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        print("✅ JWT token verified successfully")
        return payload
    except jwt.ExpiredSignatureError:
        print("❌ JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid JWT token: {e}")
        return None