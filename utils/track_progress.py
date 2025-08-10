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
    
    async def notify_progress(self, session_id: str, step: str, status: str, details = None):
        """Notify all callbacks for a session with throttling for streaming"""
        if session_id in self.callbacks:
            # For streaming updates, throttle to avoid overwhelming the frontend
            if step == "streaming" and status == "partial":
                # Use a simple throttling mechanism - only update every ~50ms
                current_time = asyncio.get_event_loop().time()
                last_update_key = f"{session_id}_last_stream"
                
                if not hasattr(self, '_last_updates'):
                    self._last_updates = {}
                    
                if (last_update_key in self._last_updates and 
                    current_time - self._last_updates[last_update_key] < 0.05):  # 50ms throttle
                    return
                    
                self._last_updates[last_update_key] = current_time
            
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