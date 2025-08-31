"""
Configuration management for the application
"""
import os
import secrets


class Config:
    """Application configuration"""
    
    # JWT Configuration
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
    IS_PRODUCTION = False  # os.getenv("ENVIRONMENT", "production").lower() == "production"
    COOKIE_SECURE = IS_PRODUCTION  # Only send cookies over HTTPS in production
    
    # CORS Configuration
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://localhost:8000",
        "https://127.0.0.1:8000",
    ]
    
    # Add production origins from environment variable
    if prod_origins := os.getenv("ALLOWED_ORIGINS"):
        ALLOWED_ORIGINS.extend(prod_origins.split(","))
    
    @classmethod
    def print_config(cls):
        """Print configuration status"""
        print(f"🔧 Environment: {'production' if cls.IS_PRODUCTION else 'development'}")
        print(f"🔧 Cookie secure: {cls.COOKIE_SECURE}")
        print(f"🔧 MongoDB URL: {cls.MONGODB_URL}")
        print(f"🔧 Database: {cls.DATABASE_NAME}")