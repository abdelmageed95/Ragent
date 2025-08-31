"""
WebSocket connection handler
"""
import json
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from core.auth.jwt_handler import verify_jwt_token


async def handle_websocket_connection(websocket: WebSocket, session_id: str, app):
    """Handle WebSocket connection with authentication"""
    print(f"🔌 WebSocket connection attempt for session: {session_id}")
    await websocket.accept()
    print("✅ WebSocket accepted")
    websocket_key = None  # Initialize to prevent unbound variable
    
    try:
        # Get authentication from first message
        print("🔍 Waiting for auth message...")
        auth_data = await websocket.receive_text()
        print(f"📨 Received auth data: {auth_data}")
        auth_message = json.loads(auth_data)
        print(f"📋 Parsed auth message: {auth_message}")
        
        token = auth_message.get("auth_token")
        if not token:
            print("❌ No auth token in message")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication required"
            }))
            await websocket.close()
            return
        
        print(f"🔑 Got auth token: {token[:20]}...")
        
        # Verify token
        print("🔍 Verifying JWT token...")
        payload = verify_jwt_token(token)
        if not payload:
            print("❌ JWT token verification failed")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid or expired token"
            }))
            await websocket.close()
            return
        
        print(f"✅ JWT verified, payload: {payload}")
        user_id = payload["user_id"]
        print(f"👤 User ID from token: {user_id}")
        
        # Verify session access
        print(f"🔍 Checking session access for session {session_id}, user {user_id}")
        db = app.state.db
        session = await db.get_session_by_id(session_id, user_id)
        if not session:
            print(f"❌ Session {session_id} not accessible for user {user_id}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Session not accessible"
            }))
            await websocket.close()
            return
        
        print(f"✅ Session verified: {session.get('name', 'Unknown')}")
        
        # Register WebSocket with unique key to prevent collisions
        websocket_key = f"{user_id}:{session_id}"
        app.state.multi_agent_manager.active_websockets[websocket_key] = websocket
        
        # Send connection confirmation
        print("✅ Sending connection confirmation...")
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "user_id": user_id,
            "message": "Connected with authentication"
        }))
        print("✅ WebSocket fully connected and ready")
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                user_message = message_data.get("message", "")
                chat_mode = message_data.get("mode", "general")  # Default to general
                
                if user_message.strip():
                    try:
                        result = await app.state.multi_agent_manager.process_message(
                            user_message, user_id, session_id, chat_mode
                        )
                        
                        print(f"🔍 Sending WebSocket response with result keys: {list(result.keys())}")
                        print(f"🔍 Agent type in result: {result.get('agent_type', 'NOT FOUND')}")
                        print(f"🔍 Selected agent in result: {result.get('selected_agent', 'NOT FOUND')}")  
                        print(f"🔍 Metadata in result: {result.get('metadata', {})}")
                        print(f"🔍 Chat mode used: {chat_mode}")
                        
                        response_data = {
                            "type": "chat_response",
                            **result
                        }
                        print(f"🔍 Final response data keys: {list(response_data.keys())}")
                        print(f"🔍 Final agent_type: {response_data.get('agent_type', 'NOT FOUND')}")
                        
                        await websocket.send_text(json.dumps(response_data))
                        
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Processing failed: {str(e)}"
                        }))
            
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected normally: {session_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {type(e).__name__}: {e}")
        print(f"📍 Error occurred at session: {session_id}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print(f"🧹 Cleaning up WebSocket for session: {session_id}")
        if websocket_key and websocket_key in app.state.multi_agent_manager.active_websockets:
            del app.state.multi_agent_manager.active_websockets[websocket_key]
            print(f"✅ WebSocket cleaned up: {websocket_key}")
        else:
            print(f"⚠️ No WebSocket key to clean up: {websocket_key}")