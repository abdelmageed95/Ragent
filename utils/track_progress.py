from typing import Callable, Dict, List
import asyncio

class ProgressCallback:
    """Callback system for workflow progress tracking"""
    
    def __init__(self):
        self.callbacks: Dict[str, List[Callable]] = {}
    
    def register_callback(self, session_id: str, callback: Callable):
        """Register a progress callback for a session"""
        if session_id not in self.callbacks:
            self.callbacks[session_id] = []
        self.callbacks[session_id].append(callback)
    
    def unregister_session(self, session_id: str):
        """Remove all callbacks for a session"""
        if session_id in self.callbacks:
            del self.callbacks[session_id]
    
    async def notify_progress(self, session_id: str, step: str, status: str, details: str = None):
        """Notify all callbacks for a session"""
        if session_id in self.callbacks:
            for callback in self.callbacks[session_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(session_id, step, status, details)
                    else:
                        callback(session_id, step, status, details)
                except Exception as e:
                    print(f"Error in progress callback: {e}")

# Global progress callback system
progress_callbacks = ProgressCallback()