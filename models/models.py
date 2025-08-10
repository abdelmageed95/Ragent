from typing import Dict, Any, List, Annotated
from langgraph.graph.message import add_messages

# ===============================
# State Definition
# ===============================

class WorkflowState:
    """
    State object for the LangGraph workflow
    """
    user_message: str
    user_id: str
    thread_id: str
    messages: Annotated[list, add_messages]
    memory_context: Dict[str, Any]
    selected_agent: str
    agent_response: str
    metadata: Dict[str, Any]
    tools_used: List[str]
    wikipedia_results: List[Dict[str, Any]]
    
    def __init__(self, **kwargs):
        self.user_message = kwargs.get('user_message', '')
        self.user_id = kwargs.get('user_id', '')
        self.thread_id = kwargs.get('thread_id', '')
        self.messages = kwargs.get('messages', [])
        self.memory_context = kwargs.get('memory_context', {})
        self.selected_agent = kwargs.get('selected_agent', '')
        self.agent_response = kwargs.get('agent_response', '')
        self.metadata = kwargs.get('metadata', {})
        self.tools_used = kwargs.get('tools_used', [])
        self.wikipedia_results = kwargs.get('wikipedia_results', [])


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