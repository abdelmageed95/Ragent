# Multi-Agent AI System - FastAPI Integration Guide

## 🚀 Complete Setup Instructions

### 1. Project Structure
```
multi-agent-system/
├── main.py                 # FastAPI backend (use the provided code)
├── your_langgraph_system.py # Your existing LangGraph system
├── memory.py               # Your memory system (if available)
├── rag.py                  # Your RAG system (if available)
├── static/
│   └── index.html         # Dashboard UI (use the integrated dashboard)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── README.md              # This guide
```

### 2. Requirements Installation

Create `requirements.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-multipart==0.0.6
pydantic==2.5.0
langchain==0.1.0
langchain-openai==0.0.2
langgraph==0.0.26
openai==1.6.1
wikipedia==1.4.0
python-dotenv==1.0.0
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_TRACING_V2=false
ENVIRONMENT=development
DEBUG=true
```

### 4. Backend Integration Steps

#### Step 1: Update Import Path
In `main.py`, update this line:
```python
from your_langgraph_system import (  # Replace with your actual module name
    LangGraphMultiAgentSystem,
    create_langgraph_system,
    MemoryAgent,
    MemoryConfig
)
```

#### Step 2: Add Missing Import
Add to the top of `main.py`:
```python
import os
```

#### Step 3: Update Your LangGraph System
Ensure your `your_langgraph_system.py` has these imports:
```python
from memory import MemoryAgent, MemoryConfig  # Make optional
from rag import RagAgent, rag_answer          # Make optional
```

### 5. Frontend Setup

#### Step 1: Save Dashboard HTML
Save the "Integrated Dashboard with WebSocket Support" artifact as `static/index.html`

#### Step 2: Update FastAPI to Serve Static Files
Uncomment this line in `main.py`:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

#### Step 3: Update Dashboard Route
Replace the `/dashboard` route in `main.py`:
```python
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML"""
    return FileResponse("static/index.html")
```

### 6. Running the System

#### Development Mode
```bash
# Start the FastAPI server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. API Endpoints

Once running, your system will have:

- **Dashboard**: `http://localhost:8000/dashboard`
- **Health Check**: `GET http://localhost:8000/health`
- **REST Chat**: `POST http://localhost:8000/api/chat`
- **WebSocket**: `ws://localhost:8000/ws/{session_id}?user_id={user_id}`
- **API Docs**: `http://localhost:8000/docs`
- **Agents Info**: `GET http://localhost:8000/api/agents`

### 8. WebSocket Message Format

#### Client to Server:
```json
{
  "type": "chat_message",
  "message": "Hello, tell me about AI",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Server to Client:
```json
{
  "type": "chat_response",
  "response": "AI is...",
  "agent_used": "chatbot",
  "tools_used": ["search_wikipedia"],
  "metadata": {...},
  "processing_time_ms": 1500,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 9. Customization Options

#### Adding New Agents
1. Update the `agents` list in `MultiAgentManager`
2. Add agent info to `/api/agents` endpoint
3. Update agent mapping in dashboard JavaScript

#### Custom Authentication
Replace the `get_current_user` dependency:
```python
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Your authentication logic here
    return {"user_id": "authenticated_user", "is_authenticated": True}
```

#### Database Integration
Add database models and connections:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
engine = create_engine("sqlite:///./conversations.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### 10. Testing

#### Test WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/test_session?user_id=test_user');
ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log('Received:', JSON.parse(event.data));
ws.send(JSON.stringify({
  type: 'chat_message',
  message: 'Hello AI!',
  timestamp: new Date().toISOString()
}));
```

#### Test REST API
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello AI!",
    "user_id": "test_user",
    "thread_id": "test_thread"
  }'
```

### 11. Deployment

#### Docker Deployment
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Environment Variables for Production
```env
OPENAI_API_KEY=your_production_key
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=your-domain.com
```

### 12. Monitoring & Logging

#### Add Structured Logging
```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### 13. Troubleshooting

#### Common Issues:

1. **WebSocket Connection Failed**
   - Check if port 8000 is available
   - Verify firewall settings
   - Test with `ws://localhost:8000/ws/test?user_id=test`

2. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path and module names
   - Verify your LangGraph system is properly structured

3. **Memory/RAG System Unavailable**
   - The system uses mock implementations when real systems aren't available
   - Check import paths in your modules

4. **CORS Issues**
   - Update CORS settings in FastAPI configuration
   - Ensure frontend and backend are on same domain in production

### 14. Features Overview

✅ **Real-time WebSocket Communication**
✅ **Multi-agent Workflow Visualization**  
✅ **RESTful API Endpoints**
✅ **Professional Dashboard UI**
✅ **Agent Status Indicators**
✅ **Tool Usage Tracking**
✅ **Memory Context Management**
✅ **Wikipedia Integration**
✅ **Export Conversations**
✅ **Health Monitoring**
✅ **Error Handling & Recovery**
✅ **Mobile Responsive Design**

### 15. Next Steps

1. **Start the system**: `python main.py`
2. **Open dashboard**: Visit `http://localhost:8000/dashboard`
3. **Test functionality**: Use the "Try Demo" button
4. **Customize agents**: Modify according to your needs
5. **Deploy to production**: Use Docker or cloud platform

## 🎉 Your multi-agent AI system is now ready with a professional UI!

The system provides a complete integration between your LangGraph multi-agent system and a modern web interface with real-time communication capabilities.