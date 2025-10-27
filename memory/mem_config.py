
import os
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer


# ---------------------------
# Memory Configuration
# ---------------------------
@dataclass
class MemoryConfig:
    # ChromaDB settings (for long-term vector memory)
    chroma_db_dir: str = os.getenv("CHROMA_DB_DIR", "data/chroma_db")
    memory_collection_prefix: str = "memory"  # Will be memory_{user_id}_{thread_id}

    # MongoDB settings (for structured facts & message history)
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name: str = os.getenv("MONGO_DB", "agentic_memory")

    # Short-term buffer size (user+assistant turns)
    short_term_window: int = int(os.getenv("SHORT_TERM_WINDOW", "6"))

    # Local embeddings model for long-term memory (free, no API costs)
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embeddings: SentenceTransformer = field(default=None)

    def __post_init__(self):
        """Initialize the embeddings model after dataclass creation"""
        if self.embeddings is None:
            self.embeddings = SentenceTransformer(self.embedding_model_name)
