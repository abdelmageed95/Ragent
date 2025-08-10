

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
from langchain.docstore.document import Document
#from langchain.vectorstores import Qdrant as LCQdrant
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from pymongo import MongoClient
from langchain_qdrant import Qdrant as LCQdrant
from openai import OpenAI
from memory.mem_config import MemoryConfig

from dotenv import load_dotenv
load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------
# Memory Agent
# ---------------------------
class MemoryAgent:
    """
    Agentic memory manager handling:
      - Short-term conversational context (in-memory)
      - Long-term semantic memory (Qdrant)
      - Structured user facts (MongoDB using LLM extraction)
      - Persistent message history for UI pagination (MongoDB)

    Uses OpenAI text-embedding-3-small for long-term embeddings and GPT-4o Mini to extract facts.
    """
    def __init__(
        self,
        user_id: str,
        thread_id: str,
        cfg: Optional[MemoryConfig] = None,
    ) -> None:
        self.user_id = str(user_id)
        self.thread_id = str(thread_id)
        self.cfg = cfg or MemoryConfig()

        # ----- Qdrant long-term memory -----
        self.qdrant_client = QdrantClient(
            url=self.cfg.qdrant_url,
            api_key=self.cfg.qdrant_api_key
        )
      
        self.collection_name = f"mem_{self.user_id}_{self.thread_id}"
        self._ensure_qdrant_collection()
        self.qdrant_store = LCQdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.cfg.embeddings,
        )

        # ----- MongoDB structured facts & history -----
        self.mongo = MongoClient(self.cfg.mongo_uri)
        self.mongo_db = self.mongo[self.cfg.db_name]
        self.facts_col = self.mongo_db["user_facts"]
        self.messages_col = self.mongo_db["messages_history"]

        # ----- In-memory short-term buffer -----
        self._short_term: List[Dict[str, str]] = []

    def _ensure_qdrant_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""
        if not self.qdrant_client.collection_exists(self.collection_name):
            dim = len(self.cfg.embeddings.embed_query("test query"))
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=dim,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def fetch_short_term(self) -> List[Dict[str,Any]]:
        # pull the last N messages from Mongo instead of the in‑memory list
        cursor = self.messages_col.find(
            {"user_id": self.user_id, "thread_id": self.thread_id}
        ).sort("timestamp", -1).limit(self.cfg.short_term_window * 2)
        # reverse so oldest→newest
        return list(cursor)[::-1]


    def fetch_history(
        self,
        page: int = 0,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """Return paginated conversation history."""
        skip = page * page_size
        cursor = self.messages_col.find(
            {"user_id": self.user_id, "thread_id": self.thread_id}
        ).sort("timestamp", 1).skip(skip).limit(page_size)
        return list(cursor)

    def fetch_long_term(
        self,
        query: Optional[str] = None,
        k: int = 5,
    ) -> List[Document]:
        """Semantic recall of past conversation turns."""
        if query is None and self._short_term and self._short_term[-1]["role"] == "user":
            query = self._short_term[-1]["content"]
        if not query:
            return []
        return self.qdrant_store.similarity_search(query, k=k)

    def get_user_facts(self) -> Dict[str, Any]:
        """Retrieve the deduplicated facts dictionary for this user."""
        doc = self.facts_col.find_one({"user_id": self.user_id}) or {}
        # 'facts' is stored as a dict; return it directly
        return doc.get("facts", {})

    def update(self, user_message: str, assistant_message: str) -> None:
        """
        Append new messages, persist history, long-term memory, and update facts.
        """
        timestamp = datetime.now()

        # 1) Short-term buffer
        self._short_term.append({"role": "user", "content": user_message})
        self._short_term.append({"role": "assistant", "content": assistant_message})
        excess = len(self._short_term) - (self.cfg.short_term_window * 2)
        if excess > 0:
            self._short_term = self._short_term[excess:]

        # 2) Persist messages
        self.messages_col.insert_many([
            {"user_id": self.user_id, "thread_id": self.thread_id, "role": "user", "content": user_message, "timestamp": timestamp},
            {"user_id": self.user_id, "thread_id": self.thread_id, "role": "assistant", "content": assistant_message, "timestamp": timestamp},
        ])

        # 3) Persist long-term memory
        combined = f"User: {user_message}\nAssistant: {assistant_message}"
        doc = Document(page_content=combined, metadata={
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "timestamp": timestamp.isoformat(),
        })
        self.qdrant_store.add_documents([doc])

        # 4) Merge and update facts
        existing = self.get_user_facts()  # existing dict
        new = self.extract_facts(user_message) or {}
        merged = {**existing, **new}
        if merged:
            self.facts_col.update_one(
                {"user_id": self.user_id},
                {"$set": {"facts": merged, "last_update": timestamp}},
                upsert=True,
            )
        
    @staticmethod
    def extract_facts(text: str) -> Dict[str, str]:
        """
        Use an LLM (GPT-4o Mini) to extract personal/info facts from text.
        Returns a dict of key/value pairs.
        """
        prompt = (
            "Extract any personal profile information and relevant facts from the following text. "
            "Return ONLY a JSON object with key/value pairs, no additional text, no explanations."
             "If there is no relevant information in the text, return an empty object.\n\n"
            f"Text: {text}"
        )
        try:
            resp = openai_client.chat.completions.create(
                model = "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an assistant that extracts personal user information as JSON."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0
            )
            content = resp.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            print(f"Fact extraction error: {e}")
            return {}


# Mock memory agent for testing when real memory system isn't available 
class MockMemoryAgent:
    """Mock memory agent for testing when real memory system isn't available"""
    
    def update(self, user_message: str, agent_response: str):
        print(f"📝 Enhanced Mock memory: Saved conversation (user: {len(user_message)} chars, agent: {len(agent_response)} chars)")
        return True