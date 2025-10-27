# Memory Agent System

The Memory Agent is a comprehensive memory management system for the agentic AI application that handles conversational context, user facts, and long-term semantic memory storage.

## Architecture Overview

The memory system operates on three distinct layers:

1. **Short-term Memory**: Recent conversation context (in-memory buffer)
2. **Long-term Memory**: Semantic embeddings for conversation retrieval (ChromaDB vector store)
3. **User Facts**: Structured personal information extracted from conversations (MongoDB)
4. **Message Persistence**: Unified conversation storage (MongoDB conversations collection)

## Components

### Core Files

- `mem_agent.py` - Main MemoryAgent class implementation
- `mem_config.py` - Configuration settings for memory system
- `README.md` - This documentation file

## Memory Agent Class

### Initialization

```python
from memory.mem_agent import MemoryAgent
from memory.mem_config import MemoryConfig

memory_agent = MemoryAgent(
    user_id="user_123",
    thread_id="session_456", 
    cfg=MemoryConfig()
)
```

**Parameters:**
- `user_id`: Unique identifier for the user
- `thread_id`: Session/conversation thread identifier
- `cfg`: Memory configuration object (optional)

### Memory Operations

#### 1. Fetch Short-term Memory

Retrieves recent conversation messages from the unified database collection.

```python
recent_messages = memory_agent.fetch_short_term()
```

**Returns:** List of recent conversation messages (user and assistant roles)

**Implementation:**
- Queries `conversations` collection by `user_id` and `thread_id`
- Sorts by timestamp (newest first)
- Limits to configured window size (`short_term_window * 2`)
- Reverses to chronological order (oldest → newest)

#### 2. Fetch Long-term Memory

Performs semantic search on past conversations using vector embeddings.

```python
relevant_docs = memory_agent.fetch_long_term(
    query="user's current question",
    k=5  # number of results
)
```

**Returns:** List of Document objects with relevant conversation content

**Implementation:**
- Uses ChromaDB vector store for similarity search
- Embeds query using local sentence-transformers (all-MiniLM-L6-v2)
- Returns most semantically similar past conversations

#### 3. Get User Facts

Retrieves structured personal information about the user.

```python
user_facts = memory_agent.get_user_facts()
```

**Returns:** Dictionary of extracted user facts and preferences

**Example:**
```python
{
    "name": "John Doe",
    "location": "San Francisco", 
    "occupation": "Software Engineer",
    "preferences": "Likes Python programming"
}
```

#### 4. Update Memory (Legacy - Deprecated)

⚠️ **Note**: This method is deprecated for the unified database system.

```python
# DON'T USE - Causes duplicate message storage
memory_agent.update(user_message, assistant_response)
```

#### 5. Update Facts and Embeddings (Recommended)

Updates memory context without duplicate message persistence.

```python
memory_agent.update_facts_and_embeddings(user_message, assistant_response)
```

**What it does:**
- Updates in-memory short-term buffer for context
- Adds conversation to ChromaDB vector store for semantic search
- Extracts and updates user facts using LLM
- **Does NOT** save messages to database (handled by main app)

## Memory Configuration

### MemoryConfig Class

Located in `mem_config.py`, contains all memory system settings:

```python
class MemoryConfig:
    # Database connections
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "agentic_memory"
    chroma_db_dir: str = "data/chroma_db"

    # Memory settings
    short_term_window: int = 10  # Number of recent message pairs
    memory_collection_prefix: str = "memory"

    # AI models
    embedding_model_name: str = "all-MiniLM-L6-v2"  # Local, free embeddings
    embeddings: SentenceTransformer  # For vector storage
```

## Database Schema

### Conversations Collection (Unified)

Used by both UI and memory system:

```javascript
{
  "_id": ObjectId,
  "session_id": ObjectId,     // For UI session management
  "thread_id": String,        // For memory agent queries  
  "user_id": ObjectId,
  "role": "user|assistant",
  "content": String,
  "metadata": Object,
  "timestamp": Date,
  "message_pair_id": String   // Links user-assistant pairs
}
```

**Indexes:**
- `{session_id: 1, timestamp: 1}` - UI message retrieval
- `{user_id: 1, thread_id: 1, timestamp: 1}` - Memory queries

### User Facts Collection

Stores extracted structured information:

```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "facts": Object,           // Key-value pairs of user information
  "last_update": Date
}
```

### ChromaDB Vector Store

Collection per user-thread: `memory_{user_id}_{thread_id}`

Stores conversation embeddings for semantic search:
- **Vectors**: 384-dimensional embeddings (all-MiniLM-L6-v2)
- **Metadata**: `{user_id, thread_id, timestamp}`
- **Content**: Combined user-assistant conversation pairs
- **Storage**: File-based in `data/chroma_db/` directory

## Integration with Main Application

### Memory Workflow Integration

The memory system integrates with the LangGraph workflow through memory nodes:

1. **Memory Fetch Node** (`graph/memory_nodes.py`):
   - Loads conversation context at workflow start
   - Fetches short-term, long-term, and user facts
   - Provides context to AI agents

2. **Memory Update Node** (`graph/memory_nodes.py`):
   - Called after agent processing
   - Updates facts and embeddings only
   - Avoids duplicate message storage

### Usage in Workflow

```python
# In workflow nodes
async def enhanced_memory_fetch_node(state):
    memory_agent = MemoryAgent(
        user_id=state["user_id"],
        thread_id=state["thread_id"]
    )
    
    # Load all memory types
    short_term = memory_agent.fetch_short_term()
    long_term = memory_agent.fetch_long_term(state["user_message"])
    user_facts = memory_agent.get_user_facts()
    
    return {
        **state,
        "memory_context": {
            "short_term": short_term,
            "long_term": long_term,
            "user_facts": user_facts,
            "memory_agent": memory_agent
        }
    }

async def enhanced_memory_update_node(state):
    memory_agent = state["memory_context"]["memory_agent"]
    
    # Update facts and embeddings only (no message duplication)
    memory_agent.update_facts_and_embeddings(
        state["user_message"], 
        state["agent_response"]
    )
```

## LLM-based Fact Extraction

The system uses GPT-4o Mini to extract structured information from user messages:

### Extraction Process

1. **Input**: User message text
2. **Prompt**: Instructs LLM to extract personal facts as JSON
3. **Output**: Key-value pairs of user information
4. **Storage**: Merged with existing facts (new facts override old ones)

### Example Extraction

**Input**: "I'm John, a software engineer from San Francisco. I love Python programming."

**Extracted Facts**:
```json
{
  "name": "John",
  "occupation": "software engineer", 
  "location": "San Francisco",
  "programming_preference": "Python"
}
```

## Error Handling & Fallbacks

### MockMemoryAgent

For testing or when dependencies are unavailable:

```python
from memory.mem_agent import MockMemoryAgent

# Fallback agent that logs operations without storage
mock_agent = MockMemoryAgent()
mock_agent.update_facts_and_embeddings("test", "response")
```

### Connection Failures

- MongoDB connection failures fall back to empty results
- Qdrant connection failures return empty similarity search
- LLM fact extraction failures are logged and ignored

## Environment Setup

### Required Environment Variables

```bash
# OpenAI API (for fact extraction only - GPT-4o Mini)
OPENAI_API_KEY=your_openai_api_key

# MongoDB (for facts and conversation storage)
MONGODB_URL=mongodb://localhost:27017

# ChromaDB (optional - defaults shown)
CHROMA_DB_DIR=data/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Docker Services

```yaml
# docker-compose.yml
services:
  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
```

**Note**: ChromaDB is file-based and requires no separate service.

## Performance Considerations

### Optimization Strategies

1. **Short-term Buffer**: In-memory caching of recent messages
2. **Vector Indexing**: ChromaDB provides fast similarity search
3. **Fact Merging**: Only extracts facts from user messages (not assistant)
4. **Lazy Loading**: Collections created only when needed
5. **Local Embeddings**: No API latency, faster generation

### Memory Limits

- Short-term buffer: Configurable window (default: 10 message pairs)
- Long-term search: Configurable K value (default: 5 results)
- Fact storage: No hard limit (merged dictionary)

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**:
   - Ensure MongoDB service is running
   - Check MongoDB connection URL and port
   - ChromaDB requires no separate service

2. **"Collection not found" errors**:
   - Collections are auto-created on first use
   - Verify database permissions

3. **Duplicate messages**:
   - Use `update_facts_and_embeddings()` instead of `update()`
   - Ensure main app handles message persistence

4. **Empty memory context**:
   - Check user_id and thread_id consistency
   - Verify database indexes are created

### Debug Logging

Enable debug logging to trace memory operations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Memory operations will now log detailed information
memory_agent.fetch_short_term()
```

## Migration from Legacy System

### From Dual Collections

The system was migrated from separate `messages` and `messages_history` collections to a unified `conversations` collection:

**Before**:
- `messages` (UI) + `messages_history` (Memory) = Duplication
- Different schemas and access patterns

**After**:
- Single `conversations` collection serves both purposes
- Unified schema with role-based messages
- No duplication, better consistency

### Backward Compatibility

Legacy methods are maintained for compatibility:
- `update()` method still exists but logs deprecation warning
- Old collection queries gracefully fail to new unified collection

## Future Enhancements

### Planned Features

1. **Memory Compression**: Summarize old conversations to save space
2. **Privacy Controls**: User-controlled fact deletion and retention
3. **Multi-modal Memory**: Support for image and audio conversation context
4. **Federated Search**: Cross-user knowledge sharing with privacy controls

### Configuration Extensions

```python
class EnhancedMemoryConfig(MemoryConfig):
    # Future options
    enable_compression: bool = False
    max_long_term_entries: int = 1000
    fact_retention_days: int = 365
    enable_cross_user_search: bool = False
```

---

## Recent Updates

### ChromaDB Migration (October 2025)

The Memory Agent has been migrated from Qdrant to ChromaDB for long-term memory storage:

- **Previous**: Qdrant vector database + OpenAI embeddings (paid)
- **Current**: ChromaDB (file-based) + Local sentence-transformers (free)

**Benefits**:
- Simplified stack (no separate vector database service)
- Zero API costs for embeddings
- Unified technology with RAG system
- Offline capability
- Better data privacy

See `MEMORY_CHROMADB_MIGRATION.md` for detailed migration information.

---

For questions or issues related to the memory system, check the main application logs or refer to the troubleshooting section above.