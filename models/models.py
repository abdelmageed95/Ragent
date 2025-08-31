from typing import Dict, Any, List, Annotated, Optional
from langgraph.graph.message import add_messages
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ===============================
# LangGraph State Definitions
# ===============================


class EnhancedWorkflowState:
    """Enhanced state object with progress tracking"""

    def __init__(self, **kwargs):
        self.user_message: str = kwargs.get('user_message', '')
        self.user_id: str = kwargs.get('user_id', '')
        self.thread_id: str = kwargs.get('thread_id', '')
        self.session_id: str = kwargs.get('session_id', '')  # For progress tracking
        self.messages: Annotated[list, add_messages] = kwargs.get('messages', [])
        self.memory_context: Dict[str, Any] = kwargs.get('memory_context', {})
        self.selected_agent: str = kwargs.get('selected_agent', '')
        self.agent_response: str = kwargs.get('agent_response', '')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
        self.tools_used: List[str] = kwargs.get('tools_used', [])
        self.wikipedia_results: List[Dict[str, Any]] = kwargs.get('wikipedia_results', [])

        # Progress tracking
        self.current_step: str = kwargs.get('current_step', '')
        self.step_details: Dict[str, Any] = kwargs.get('step_details', {})


# ===============================
# Database Models
# ===============================


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    last_active: datetime
    session_count: int
    total_messages: int
    is_active: bool


class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SessionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SessionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    last_active: datetime
    message_count: int
    tools_used: int
    is_active: bool


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None


# ConversationMessage removed - handled directly by DatabaseManager
