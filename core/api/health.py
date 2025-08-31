"""
Health check API routes
"""
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check(request):
    """Health check with database status"""
    try:
        # Test database connection
        db = request.app.state.db
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