# Simple RAG System Guide

A streamlined, text-only RAG (Retrieval-Augmented Generation) system without the complexity of image processing or Docling.

## Overview

This simplified RAG system focuses on **text-only** processing with:
- Simple PDF text extraction using `pypdf`
- Local embeddings with Sentence Transformers (no API costs)
- ChromaDB vector database for persistent storage
- Single LLM call for answer generation (efficient)
- Clean, easy-to-understand codebase
- Multi-agent orchestration with LangGraph

## Key Components

### 1. PDF Text Extractor (`rag_agent/pdf_extractor.py`)
Simple utility for extracting text from PDFs without complex dependencies.

```python
from rag_agent.pdf_extractor import SimplePDFExtractor

extractor = SimplePDFExtractor()
text = extractor.extract_text("document.pdf")
chunks = extractor.chunk_text(text, chunk_size=500, overlap=50)
```

### 2. Knowledge Base Builder (`rag_agent/build_kb_simple.py`)
Builds a ChromaDB collection from PDF documents.

```python
from rag_agent.build_kb_simple import build_text_index

pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
build_text_index(
    pdf_paths=pdf_files,
    collection_name="documents",
    chunk_size=500,
    chunk_overlap=50,
    reset_collection=False  # Set to True to rebuild from scratch
)
```

### 3. RAG Agent (`rag_agent/ragagent_simple.py`)
Handles retrieval and generation with a clean API.

```python
from rag_agent.ragagent_simple import SimpleRagAgent

agent = SimpleRagAgent(collection_name="documents")
answer, metadata = agent.answer_query("What is this about?", top_k=5)
print(answer)
```

## Quick Start

### 1. Install Dependencies

```bash
# Install minimal dependencies for simple RAG
pip install pypdf sentence-transformers torch chromadb openai python-dotenv numpy
```

Or install from requirements.txt (includes all dependencies including multi-agent system):
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Prepare Your PDFs

Create a `pdfs/` folder and add your PDF documents:
```bash
mkdir -p pdfs
# Copy your PDF files to pdfs/
```

### 4. Build the Knowledge Base

```bash
python -m rag_agent.build_kb_simple
```

This will:
- Extract text from all PDFs in the `pdfs/` folder
- Chunk the text into manageable pieces
- Generate embeddings using local models (free!)
- Build and save a ChromaDB collection to `data/chroma_db/`
- Store both embeddings and metadata together in ChromaDB

### 5. Query Your Documents

```bash
# Interactive query
python -m rag_agent.ragagent_simple "What is machine learning?"
```

Or use in your code:
```python
from rag_agent.ragagent_simple import rag_answer

answer, metadata = rag_answer("What is machine learning?", top_k=5)
print(f"Answer: {answer}")
print(f"Sources: {metadata['sources']}")
```

## Architecture

```
┌─────────────────┐
│   PDF Files     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│  SimplePDFExtractor     │  Extract text
│  - pypdf                │
│  - Text chunking        │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  Local Embeddings       │  Generate vectors (FREE)
│  - Sentence Transformers│
│  - No API calls         │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  ChromaDB Collection    │  Store vectors + metadata
│  - Persistent storage   │
│  - Built-in filtering   │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  User Query             │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  Retrieve (top-k)       │  Find relevant chunks
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  LLM Generation         │  Single API call
│  - OpenAI GPT-4o-mini   │
│  - Context + Query      │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│  Answer                 │
└─────────────────────────┘
```

## Differences from Complex RAG

| Feature | Complex RAG (old) | Simple RAG (new) |
|---------|------------------|------------------|
| PDF Processing | Docling (heavy) | pypdf (simple) |
| Modalities | Text + Images | Text only |
| Embeddings | Text + Image vectors | Text only |
| Vector DB | FAISS (2 indices) | ChromaDB (1 collection) |
| LLM Calls | N+1 per query | 1 per query |
| Dependencies | Many (Docling, OCR, etc.) | Core only |
| Setup Complexity | High | Low |
| Performance | Slower (multiple APIs) | Faster (single call) |
| Cost | Higher (multiple calls) | Lower (single call) |
| Persistence | Manual (pickle files) | Built-in (ChromaDB) |

## API Reference

### SimplePDFExtractor

```python
extractor = SimplePDFExtractor()

# Extract all text from PDF
text = extractor.extract_text(pdf_path: str) -> str

# Chunk text into smaller pieces
chunks = extractor.chunk_text(
    text: str,
    chunk_size: int = 500,    # words per chunk
    overlap: int = 50          # overlapping words
) -> List[str]
```

### build_text_index

```python
from rag_agent.build_kb_simple import build_text_index

build_text_index(
    pdf_paths: List[str],                                    # PDF files to process
    index_path: str = "data/faiss_text_simple.index",        # FAISS index output
    meta_path: str = "data/text_meta_simple.pkl",            # Metadata output
    chunk_size: int = 500,                                   # Words per chunk
    chunk_overlap: int = 50                                  # Overlap
)
```

### SimpleRagAgent

```python
from rag_agent.ragagent_simple import SimpleRagAgent

agent = SimpleRagAgent(
    index_path: str = "data/faiss_text_simple.index",
    meta_path: str = "data/text_meta_simple.pkl"
)

# Retrieve relevant chunks
chunks = agent.retrieve(query: str, top_k: int = 5) -> List[Dict]

# Generate answer from chunks
answer = agent.generate_answer(
    query: str,
    context_chunks: List[Dict]
) -> str

# Complete pipeline (retrieve + generate)
answer, metadata = agent.answer_query(
    query: str,
    top_k: int = 5
) -> Tuple[str, Dict]
```

## Configuration

### Chunk Size Tuning

- **Small chunks (200-300 words)**: More precise retrieval, less context
- **Medium chunks (500-700 words)**: Balanced (recommended)
- **Large chunks (1000+ words)**: More context, less precise

### Top-k Tuning

- **k=3**: Fast, focused answers
- **k=5**: Balanced (recommended)
- **k=10**: Comprehensive, but slower and more expensive

### Model Configuration

The simple RAG system uses:
- **Embeddings**: Sentence Transformers (local, free)
- **LLM**: OpenAI GPT-4o-mini (good balance of quality and cost)

To change the LLM model, edit `ragagent_simple.py:121`:
```python
model="gpt-4o-mini"  # or "gpt-4o", "gpt-3.5-turbo", etc.
```

## Troubleshooting

### "FAISS index not found"
Run the knowledge base builder first:
```bash
python -m rag_agent.build_kb_simple
```

### "No text content extracted"
- Check if PDFs are text-based (not scanned images)
- For scanned PDFs, you'll need OCR (use the complex RAG with Docling)

### "OPENAI_API_KEY not found"
Add your API key to `.env`:
```bash
echo "OPENAI_API_KEY=your_key_here" > .env
```

### Poor retrieval quality
- Increase `top_k` (try 10 instead of 5)
- Adjust chunk size (try 300 or 700 words)
- Check if documents contain relevant information

## Cost Comparison

### Per 1000 Queries

| Component | Complex RAG | Simple RAG | Savings |
|-----------|-------------|------------|---------|
| Embeddings (Cohere) | $5-10 | $0 (local) | 100% |
| LLM calls | $2-4 (N+1 calls) | $0.50-1 (1 call) | 75% |
| **Total** | **$7-14** | **$0.50-1** | **~90%** |

## Next Steps

Once comfortable with simple RAG, you can:

1. **Add caching** for frequent queries
2. **Implement hybrid search** (keyword + semantic)
3. **Add metadata filtering** (by date, source, etc.)
4. **Upgrade to ChromaDB** for better persistence
5. **Add local LLM** with Ollama for zero API costs

See `ENHANCEMENT_PLAN.md` for advanced features.

## Files Created

```
rag_agent/
├── pdf_extractor.py          # Simple PDF text extraction
├── build_kb_simple.py         # Knowledge base builder
├── ragagent_simple.py         # RAG agent
└── embedding_helpers.py       # (existing) Embedding utilities

data/
├── faiss_text_simple.index    # Vector index
└── text_meta_simple.pkl       # Metadata
```

## License

Same as the main project.
