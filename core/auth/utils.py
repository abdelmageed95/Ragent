"""
Authentication utilities
"""
import bcrypt


def hash_password(password: str) -> bytes:
    """Hash password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)