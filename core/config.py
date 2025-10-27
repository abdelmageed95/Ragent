"""
Configuration management for the application
"""
import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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

    # Guardrails Configuration
    ENABLE_GUARDRAILS = os.getenv("ENABLE_GUARDRAILS", "true").lower() == "true"
    MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "10000"))
    MAX_OUTPUT_LENGTH = int(os.getenv("MAX_OUTPUT_LENGTH", "5000"))
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
    MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", "500"))
    ENABLE_PII_DETECTION = os.getenv("ENABLE_PII_DETECTION", "true").lower() == "true"
    REDACT_PII_IN_OUTPUT = os.getenv("REDACT_PII_IN_OUTPUT", "true").lower() == "true"

    @classmethod
    def print_config(cls):
        """Print configuration status"""
        print(f"🔧 Environment: {'production' if cls.IS_PRODUCTION else 'development'}")
        print(f"🔧 Cookie secure: {cls.COOKIE_SECURE}")
        print(f"🔧 MongoDB URL: {cls.MONGODB_URL}")
        print(f"🔧 Database: {cls.DATABASE_NAME}")
        print(f"🛡️  Guardrails enabled: {cls.ENABLE_GUARDRAILS}")
        print(f"🛡️  Rate limiting: {cls.ENABLE_RATE_LIMITING}")