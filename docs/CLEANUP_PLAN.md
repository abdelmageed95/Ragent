# Cleanup Plan for Simple Text-Only RAG

## Summary

For a simple text-only RAG system, many files can be removed or moved to archive.

## Files to Keep (Essential)

### rag_agent/ (Simplified RAG)
- ✅ `pdf_extractor.py` - Simple PDF text extraction
- ✅ `build_kb_simple.py` - Simple knowledge base builder
- ✅ `ragagent_simple.py` - Simple RAG agent
- ✅ `embedding_helpers.py` - Embedding utilities (modified to be simple)
- ✅ `local_embeddings.py` - Local embedding models

## Files to Remove or Archive

### rag_agent/ (Complex/Legacy)
- ❌ `build_kb_legacy.py` - Legacy knowledge base builder
- ❌ `build_kb.py` - Complex Docling-based builder
- ❌ `ragagent.py` - Complex multimodal RAG agent
- ❌ `ragagent_cohere.py` - Cohere-specific RAG agent
- ❌ `ragagent_optimized.py` - Optimized complex RAG
- ❌ `embedding_helpers_cohere.py` - Cohere-specific helpers
- ❌ `docling_processor.py` - Docling processor (complex)
- ❌ `vector_store.py` - ChromaDB abstraction (not needed for simple FAISS)
- ❌ `loading_helpers.py` - Multimodal index loader (not needed)

### core/ (Web Application - Optional)
**Question: Do you want to keep the web API/server or only use simple RAG via Python?**

If NO web interface needed:
- ❌ `core/api/` - All API endpoints
- ❌ `core/auth/` - Authentication system
- ❌ `core/websocket/` - WebSocket handlers
- ❌ `core/database/` - MongoDB manager
- ❌ `core/templates/` - Templates
- ⚠️ `core/cache/` - Redis caching (useful for performance, optional)
- ⚠️ `core/llm/` - LLM abstraction (useful for switching models, optional)
- ⚠️ `core/config.py` - Configuration (might be useful)

If YES web interface needed:
- ✅ Keep all of core/ (needed for FastAPI server)

### memory/ (Conversational Memory - Optional)
- ❌ `memory/mem_agent.py` - Memory agent for conversations
- ❌ `memory/mem_config.py` - Memory configuration

**Note:** Only needed if you want conversational context tracking

### graph/ (Multi-Agent Workflow - Optional)
- ❌ `graph/workflow.py` - LangGraph workflow
- ❌ `graph/chat_node.py` - Chat node
- ❌ `graph/supervisor.py` - Supervisor agent
- ❌ `graph/rag_node.py` - Complex RAG node
- ❌ `graph/rag_node_optimized.py` - Optimized RAG node
- ❌ `graph/memory_nodes.py` - Memory nodes

**Note:** Only needed if you want multi-agent orchestration

### tools/ (External Tools - Optional)
- ❌ `tools/wikipedia_tool.py` - Wikipedia search tool

**Note:** Only needed if you want external knowledge sources

## Recommended Actions

### Option 1: Minimal RAG (Library Only)
Remove everything except:
```
rag_agent/
├── pdf_extractor.py
├── build_kb_simple.py
├── ragagent_simple.py
├── embedding_helpers.py
└── local_embeddings.py
```

Use: Direct Python imports for RAG functionality

### Option 2: RAG + Web API
Keep:
```
core/                    # Web server
rag_agent/              # Simple RAG components only
├── pdf_extractor.py
├── build_kb_simple.py
├── ragagent_simple.py
├── embedding_helpers.py
└── local_embeddings.py
```

Use: FastAPI server with simple RAG backend

### Option 3: Archive Complex Features
Move to `archive/` folder:
```
archive/
├── rag_agent_complex/   # Complex multimodal RAG
├── memory/              # Memory agents
├── graph/               # Multi-agent workflows
└── tools/               # External tools
```

Keep them for reference but don't use in production

## Questions for You

1. **Do you want to keep the web API/server (FastAPI)?**
   - Yes → Keep core/
   - No → Remove core/

2. **Do you want conversational memory?**
   - Yes → Keep memory/
   - No → Remove memory/

3. **Do you want multi-agent orchestration?**
   - Yes → Keep graph/
   - No → Remove graph/

4. **Do you want external tools (Wikipedia)?**
   - Yes → Keep tools/
   - No → Remove tools/

5. **What to do with complex RAG files?**
   - Archive → Move to archive/ folder
   - Delete → Permanently remove
   - Keep → Leave as-is (not recommended)

## My Recommendation

For a **simple text-only RAG system**, I recommend:

1. ✅ Keep only simple RAG files
2. ❌ Remove or archive complex RAG files
3. ⚠️ Keep core/ IF you need web API, otherwise remove
4. ❌ Remove memory/, graph/, tools/ (not needed for basic RAG)
5. 📦 Archive complex files instead of deleting (for future reference)

This will give you a clean, simple, easy-to-maintain RAG system focused on text-only processing.

**Please let me know which option you prefer and I'll proceed with the cleanup!**
