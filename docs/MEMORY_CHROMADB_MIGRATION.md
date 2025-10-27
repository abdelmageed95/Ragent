# Memory Agent ChromaDB Migration

## Overview

The Memory Agent has been successfully migrated from **Qdrant** to **ChromaDB** for long-term semantic memory storage. This change aligns the memory system with the RAG pipeline, which already uses ChromaDB.

## Migration Date

**October 17, 2025**

## What Changed

### 1. Vector Store Backend

**Before:**
- Qdrant vector database
- Required separate service running on port 6333
- OpenAI embeddings (text-embedding-3-small) - paid API

**After:**
- ChromaDB persistent storage
- File-based storage in `data/chroma_db`
- Local sentence-transformers embeddings - FREE, no API costs
- Model: `all-MiniLM-L6-v2` (default)

### 2. Configuration Changes

**File: `memory/mem_config.py`**

Replaced Qdrant configuration with ChromaDB settings:

```python
# Old (Qdrant)
qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
embeddings: OpenAIEmbeddings = field(
    default_factory=lambda: OpenAIEmbeddings(model="text-embedding-3-small")
)

# New (ChromaDB)
chroma_db_dir: str = os.getenv("CHROMA_DB_DIR", "data/chroma_db")
memory_collection_prefix: str = "memory"
embedding_model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
embeddings: SentenceTransformer = field(default=None)
```

### 3. Memory Agent Changes

**File: `memory/mem_agent.py`**

#### Imports
- Removed: `qdrant_client`, `langchain_qdrant`, `langchain_openai`
- Added: `chromadb`, `chromadb.config.Settings`

#### Initialization
```python
# Old (Qdrant)
self.qdrant_client = QdrantClient(url=..., api_key=...)
self.qdrant_store = LCQdrant(client=..., collection_name=..., embeddings=...)

# New (ChromaDB)
self.chroma_client = chromadb.PersistentClient(
    path=self.cfg.chroma_db_dir,
    settings=Settings(anonymized_telemetry=False, allow_reset=True)
)
self.collection = self.chroma_client.get_or_create_collection(
    name=self.collection_name,
    metadata={"description": f"Long-term memory for user {user_id}, thread {thread_id}"}
)
```

#### Long-term Memory Retrieval
```python
# Old (Qdrant with LangChain)
return self.qdrant_store.similarity_search(query, k=k)

# New (ChromaDB native API)
query_embedding = self.cfg.embeddings.encode(query).tolist()
results = self.collection.query(
    query_embeddings=[query_embedding],
    n_results=min(k, self.collection.count())
)
# Convert to LangChain Document format for compatibility
```

#### Memory Updates
```python
# Old (Qdrant)
doc = Document(page_content=combined, metadata={...})
self.qdrant_store.add_documents([doc])

# New (ChromaDB)
embedding = self.cfg.embeddings.encode(combined).tolist()
doc_id = f"{self.user_id}_{self.thread_id}_{timestamp.timestamp()}"
self.collection.add(
    ids=[doc_id],
    documents=[combined],
    embeddings=[embedding],
    metadatas=[{...}]
)
```

## What Stayed the Same

### MongoDB (No Changes)
- Still used for:
  - User facts storage
  - Conversation history (unified collection)
  - Short-term memory queries

### Memory Architecture
The three-layer memory system remains unchanged:
1. **Short-term**: Recent messages (in-memory + MongoDB)
2. **Long-term**: Semantic search (now ChromaDB instead of Qdrant)
3. **User facts**: Structured info (MongoDB)

### API Compatibility
The Memory Agent API remains the same:
- `fetch_short_term()` - unchanged
- `fetch_long_term(query, k)` - same interface, different backend
- `get_user_facts()` - unchanged
- `update_facts_and_embeddings()` - same interface, different backend

## Benefits

### 1. Simplified Stack
- **Before**: MongoDB + Qdrant + OpenAI API
- **After**: MongoDB + ChromaDB (file-based)
- No need to run separate Qdrant service

### 2. Cost Savings
- **Before**: Paid OpenAI embeddings ($0.020 per 1M tokens)
- **After**: FREE local embeddings
- No ongoing API costs for memory storage

### 3. Unified Technology
- RAG system: ChromaDB ✅
- Memory system: ChromaDB ✅
- Consistent embedding models across the system

### 4. Offline Capability
- No internet required for embeddings
- All vector operations work offline
- Faster embedding generation (local GPU/CPU)

### 5. Data Privacy
- All embeddings computed locally
- No data sent to external APIs
- Complete data control

## Environment Variables

### Removed
```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=optional_key
```

### Added (Optional)
```bash
CHROMA_DB_DIR=data/chroma_db  # Default location
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Default model
```

### Still Required
```bash
OPENAI_API_KEY=your_key  # Only for fact extraction with GPT-4o Mini
MONGO_URI=mongodb://localhost:27017
MONGO_DB=agentic_memory
```

## Testing

A comprehensive test suite was created: `test_memory_chromadb.py`

**Test Results (All Passed ✅)**:
1. Memory agent initialization
2. Conversation storage with embeddings
3. User facts extraction and storage
4. Semantic search (similarity query)
5. Short-term memory retrieval
6. Collection statistics

## Migration Steps (For Reference)

If you need to migrate existing Qdrant data:

1. Export conversations from Qdrant
2. Re-generate embeddings using local model
3. Import to ChromaDB collections
4. Verify semantic search quality

**Note**: Since memory is continuously updated, no migration was necessary for this project. The system will naturally populate ChromaDB with new conversations.

## Performance Comparison

### Embedding Generation
- **OpenAI API**: ~100ms latency (network call)
- **Local Model**: ~10-50ms (depending on hardware)

### Vector Search
- **Qdrant**: Fast, requires separate service
- **ChromaDB**: Fast, embedded in application

### Storage
- **Qdrant**: Separate database files
- **ChromaDB**: `data/chroma_db/` directory

## Collection Naming

Collections are created per user-thread:

```
memory_{user_id}_{thread_id}
```

Example:
```
memory_507f1f77bcf86cd799439011_session_abc123
```

## Backward Compatibility

### Graph Nodes (No Changes Required)
The memory nodes in `graph/memory_nodes.py` work unchanged:
- `memory_fetch_node()`
- `enhanced_memory_fetch_node()`
- `memory_update_node()`
- `enhanced_memory_update_node()`

All node logic remains identical because the Memory Agent API is preserved.

## Troubleshooting

### Issue: "No module named 'chromadb'"
**Solution**: Install chromadb
```bash
pip install chromadb
```

### Issue: "No module named 'sentence_transformers'"
**Solution**: Install sentence-transformers
```bash
pip install sentence-transformers
```

### Issue: Slow first run
**Cause**: Model download on first use (~90MB for all-MiniLM-L6-v2)
**Solution**: Wait for download to complete (one-time only)

### Issue: Out of memory
**Cause**: Large embedding model
**Solution**: Use smaller model
```python
embedding_model_name: str = "all-MiniLM-L6-v2"  # Smallest
```

## Future Enhancements

### Potential Improvements
1. **Hybrid Search**: Combine semantic + keyword search
2. **Compression**: Summarize old conversations
3. **Multi-modal**: Support image/audio embeddings
4. **Distributed**: Share ChromaDB across instances

### Model Options
Can easily switch embedding models:
- `all-MiniLM-L6-v2` (current) - 384 dim, fastest
- `all-mpnet-base-v2` - 768 dim, more accurate
- `multi-qa-mpnet-base-dot-v1` - optimized for Q&A

## References

- ChromaDB: https://docs.trychroma.com/
- Sentence-Transformers: https://www.sbert.net/
- Memory Agent README: `memory/README.md`

## Summary

The Memory Agent ChromaDB migration is **complete and tested**. The system now uses:
- ✅ ChromaDB for long-term semantic memory
- ✅ Local sentence-transformers for embeddings
- ✅ MongoDB for facts and conversation history
- ✅ No external vector database service required
- ✅ FREE, offline-capable embeddings

The memory system is ready for Phase 6 enhancements!
