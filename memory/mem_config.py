
import os
from dataclasses import dataclass, field
from typing import Optional
from langchain_openai import OpenAIEmbeddings


# ---------------------------
# Memory Configuration
# ---------------------------
@dataclass
class MemoryConfig:
    # Qdrant settings (for long-term vector memory)
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")

    # MongoDB settings (for structured facts & message history)
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name: str = os.getenv("MONGO_DB", "agentic_memory")

    # Short-term buffer size (user+assistant turns)
    short_term_window: int = int(os.getenv("SHORT_TERM_WINDOW", "6"))

    # Embeddings model for long-term memory
    embeddings: OpenAIEmbeddings = field(
        default_factory=lambda: OpenAIEmbeddings(model="text-embedding-3-small")
    )
