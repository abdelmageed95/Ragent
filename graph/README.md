# Agentic Graph - LangGraph Multi-Agent Workflow System

A sophisticated multi-agent orchestration system built with LangGraph that intelligently routes user queries to specialized AI agents for optimal response generation.

## 🏗️ Architecture Overview

The agentic graph implements a **supervisor-agent pattern** where a central supervisor intelligently routes user requests to specialized agents based on content analysis and user intent.

### Workflow Diagram

```
                    ┌────────────┐
                    │   START    │
                    └────┬───────┘
                         │
                         ▼
                    ┌──────────────┐
                    │ memory_fetch │
                    └────┬─────────┘
                         │
                         ▼
                    ┌────────────┐
                    │ supervisor │
                    └────┬───────┘
                         │
               ┌────────▼────────┐
               │  route_to_agent │
               └────┬──────┬─────┘
                    ▼      ▼
               ┌───────┐ ┌────────┐
               │chatbot│ │rag_agent│
               └──┬────┘ └────┬───┘
                    ▼      ▼
               ┌────────────────┐
               │ memory_update  │
               └──────┬─────────┘
                      ▼
                    ┌────┐
                    │ END│
                    └────┘
```

## 📂 Component Structure

```
graph/
├── workflow.py         # Core workflow orchestration and system classes
├── supervisor.py       # Intelligent agent routing logic
├── memory_nodes.py     # Memory fetch and update operations
├── rag_node.py        # Document retrieval and analysis agent
├── chat_node.py       # General conversation agent with Wikipedia
└── README.md          # This documentation
```

## 🤖 Agent Descriptions

### 1. **Supervisor Agent** (`supervisor.py`)
- **Purpose**: Intelligent routing of user queries to appropriate specialized agents
- **Logic**: 
  - Fast rule-based routing using keyword analysis
  - Chat mode consideration (general, document search, etc.)
  - Fallback to chatbot for general conversations
- **Routing Rules**:
  - **RAG Agent**: Document-related keywords (search, find, pdf, analyze, etc.)
  - **Chatbot Agent**: General conversation, questions, Wikipedia queries

### 2. **Memory Agent** (`memory_nodes.py`)
- **Purpose**: Context management and conversation continuity
- **Functions**:
  - **Memory Fetch**: Retrieve conversation history and context
  - **Memory Update**: Store new interactions and maintain session state
- **Integration**: Works with MongoDB for persistent storage

### 3. **RAG Agent** (`rag_node.py`)
- **Purpose**: Document search, retrieval, and analysis
- **Capabilities**:
  - Multimodal document search (text + images)
  - FAISS vector similarity search
  - PDF content analysis
  - Source citation and evidence linking
- **Tools**: Integrates with `rag_agent.ragagent` for processing

### 4. **Chatbot Agent** (`chat_node.py`)
- **Purpose**: General conversation and knowledge queries
- **Features**:
  - Wikipedia integration for factual information
  - Natural conversation handling
  - Context-aware responses
- **Tools**: Uses Wikipedia search tools for enhanced responses

## 🔄 Workflow Process

### Standard Flow
1. **START** → Initialize request processing
2. **Memory Fetch** → Load conversation context and history
3. **Supervisor** → Analyze user intent and select appropriate agent
4. **Route to Agent** → Direct to either RAG or Chatbot agent
5. **Agent Processing** → Generate specialized response
6. **Memory Update** → Store interaction and update context
7. **END** → Return response to user

### Enhanced Flow (with Progress Tracking)
- Real-time progress updates via WebSocket
- Streaming response capabilities
- Performance monitoring and metrics
- Error handling and recovery

## 🚀 System Classes

### `LangGraphMultiAgentSystem`
Basic multi-agent system implementation with core workflow functionality.

### `EnhancedLangGraphMultiAgentSystem`
Advanced system with additional features:
- **Progress Tracking**: Real-time workflow status updates
- **Streaming Responses**: Partial response delivery
- **Performance Monitoring**: Processing time and metrics
- **Error Handling**: Robust error recovery mechanisms

## 🎯 Agent Selection Logic

### RAG Agent Triggers
```python
rag_keywords = [
    'search', 'find', 'document', 'file', 'pdf', 'image', 'upload', 
    'retrieve', 'lookup', 'query', 'database', 'knowledge', 'source',
    'reference', 'cite', 'extract', 'analyze document'
]
```

### Chat Mode Handling
- **`document`**: Forces RAG agent selection
- **`general`**: Uses keyword-based routing
- **`wikipedia`**: Routes to chatbot with Wikipedia tools

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
LANGCHAIN_TRACING_V2=false  # Disabled to avoid API errors
```

### System Initialization
```python
from graph.workflow import create_enhanced_langgraph_system

# Create system for user session
system = create_enhanced_langgraph_system(
    user_id="user_123",
    thread_id="session_456"
)

# Process message with progress tracking
result = await system.process_with_progress_tracking(
    message="Search for climate change documents",
    session_id="session_456",
    callback_func=websocket_callback,
    chat_mode="general"
)
```

## 📊 Response Structure

### Standard Response
```python
{
    "response": "Agent-generated response text",
    "agent_type": "rag_agent|chatbot",
    "selected_agent": "rag_agent|chatbot", 
    "tools_used": ["wikipedia_search", "document_search"],
    "metadata": {
        "agent_type": "rag_agent",
        "processing_time": 1.23,
        "sources": [...],
        "confidence": 0.95
    },
    "wikipedia_results": [...],  # If Wikipedia was used
    "processing_time_ms": 1234,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔄 State Management

### Workflow State Schema
```python
class EnhancedWorkflowState:
    user_message: str           # Input message
    user_id: str               # User identifier
    thread_id: str             # Session/thread identifier  
    session_id: str            # For progress tracking
    messages: List             # Conversation history
    memory_context: Dict       # Retrieved context
    selected_agent: str        # Chosen agent (rag_agent|chatbot)
    agent_response: str        # Generated response
    metadata: Dict             # Processing metadata
    tools_used: List[str]      # Tools/functions used
    wikipedia_results: List    # Wikipedia search results
    current_step: str          # Current workflow step
    step_details: Dict         # Step-specific information
```

## 🛠️ Development

### Adding New Agents

1. **Create Agent Node**:
```python
# graph/new_agent_node.py
def new_agent_node(state: Dict) -> Dict:
    # Agent logic here
    return {
        **state,
        "agent_response": response,
        "metadata": {...}
    }
```

2. **Update Supervisor Routing**:
```python
# graph/supervisor.py
if some_condition:
    return {**state, "selected_agent": "new_agent"}
```

3. **Register in Workflow**:
```python
# graph/workflow.py
workflow.add_node("new_agent", new_agent_node)
workflow.add_conditional_edges("supervisor", route_to_agent, {
    "rag_agent": "rag_agent",
    "chatbot": "chatbot", 
    "new_agent": "new_agent"  # Add new route
})
```

### Testing Agents

```python
# Test individual agent
from graph.rag_node import enhanced_rag_agent_node

state = {
    "user_message": "Find climate data",
    "user_id": "test_user",
    "thread_id": "test_session"
}

result = await enhanced_rag_agent_node(state)
print(result["agent_response"])
```

## 🔍 Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Progress Tracking
Monitor workflow execution with real-time updates:
```python
async def debug_callback(session_id, step, status, details):
    print(f"Step: {step}, Status: {status}, Details: {details}")

result = await system.process_with_progress_tracking(
    message, session_id, debug_callback
)
```

## 🚨 Error Handling

The system includes comprehensive error handling:
- **Agent Failures**: Automatic fallback to chatbot agent
- **Memory Errors**: Graceful degradation with empty context
- **Tool Failures**: Continue processing without failed tools
- **Network Issues**: Retry logic with exponential backoff

## 📈 Performance Optimization

### Caching Strategy
- **Agent Instances**: Cached per user session
- **Memory Context**: Intelligent context windowing
- **Tool Results**: Temporary caching for repeated queries

### Monitoring Metrics
- Processing time per agent
- Memory usage patterns
- Tool success rates
- Error frequency and types

## 🔮 Future Enhancements

- **Dynamic Agent Registration**: Runtime agent addition
- **Agent Learning**: Improve routing based on user feedback
- **Parallel Processing**: Multiple agents for complex queries
- **Custom Tools**: User-defined agent tools and capabilities

---

This agentic graph system provides a robust, scalable foundation for multi-agent AI interactions with intelligent routing, memory management, and real-time progress tracking.