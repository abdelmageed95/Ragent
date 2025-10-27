"""
Simple RAG Agent

A streamlined Retrieval-Augmented Generation agent for text-only processing.
No image processing, no multimodal complexity - just efficient text retrieval and generation.
"""

import os
import logging
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from rag_agent.embedding_helpers import embed_text
from core.vector_store import get_chroma_client, get_chroma_collection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ChromaDB directory
DATA_DIR = "data"
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")


class SimpleRagAgent:
    """
    Simple RAG agent for text-only retrieval and generation.

    Features:
    - Text-only retrieval from ChromaDB
    - Single LLM call for answer generation
    - Clean and straightforward pipeline
    """

    def __init__(
        self,
        collection_name: str = "documents",
        chroma_db_path: str = CHROMA_DB_DIR
    ) -> None:
        """
        Initialize the RAG agent.

        Args:
            collection_name: Name of the ChromaDB collection
            chroma_db_path: Path to ChromaDB database directory
        """
        # Check if ChromaDB exists
        if not os.path.exists(chroma_db_path):
            raise FileNotFoundError(
                f"ChromaDB not found at: {chroma_db_path}\n"
                f"Please build the knowledge base first:\n"
                f"  python -m rag_agent.build_kb_simple"
            )

        # Initialize ChromaDB using singleton manager
        logger.info("Loading ChromaDB...")
        self.client = get_chroma_client(chroma_db_path)

        # Get collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"  Loaded collection: {collection_name}")
            logger.info(f"  Document count: {self.collection.count()}")
        except Exception as e:
            raise FileNotFoundError(
                f"Collection '{collection_name}' not found.\n"
                f"Please build the knowledge base first:\n"
                f"  python -m rag_agent.build_kb_simple"
            ) from e

        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment. Add it to your .env file.")

        self.llm_client = OpenAI(api_key=openai_api_key)
        logger.info("RAG agent initialized successfully")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant text chunks for a query.

        Args:
            query: User query string
            top_k: Number of top results to return

        Returns:
            List of dictionaries containing retrieved chunks and metadata
        """
        try:
            # Embed query
            query_vec = embed_text(query)

            # Query ChromaDB
            results_data = self.collection.query(
                query_embeddings=[query_vec.tolist()],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            results = []
            if results_data and results_data['ids']:
                for i in range(len(results_data['ids'][0])):
                    metadata = results_data['metadatas'][0][i]
                    results.append({
                        "doc_id": metadata.get("doc_id", "unknown"),
                        "source": metadata.get("source", "unknown"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "score": float(results_data['distances'][0][i]),
                        "content": results_data['documents'][0][i]
                    })

            logger.info(
                f"Retrieved {len(results)} chunks for query: '{query[:50]}...'"
            )
            return results

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate an answer using retrieved context with a single LLM call.

        Args:
            query: User query
            context_chunks: List of retrieved chunks with metadata

        Returns:
            Generated answer string
        """
        if not context_chunks:
            return "I couldn't find relevant information to answer your question."

        try:
            # Format context from all chunks
            context_parts = []
            for i, chunk in enumerate(context_chunks, 1):
                context_parts.append(
                    f"[Source {i}: {chunk['source']}]\n{chunk['content']}\n"
                )

            combined_context = "\n".join(context_parts)

            # Create prompt
            system_msg = (
                "You are a helpful assistant that answers questions based on "
                "the provided context. Provide accurate, concise answers and "
                "cite sources when possible."
            )
            user_msg = (
                f"Context:\n{combined_context}\n\nQuestion: {query}\n\n"
                f"Please answer the question based on the context provided. "
                f"If the context doesn't contain enough information, say so."
            )
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]

            # Call LLM (single call!)
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer ({len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return f"Error generating answer: {str(e)}"

    def answer_query(self, query: str, top_k: int = 5) -> Tuple[str, Dict[str, Any]]:
        """
        Complete RAG pipeline: retrieve relevant chunks and generate answer.

        Args:
            query: User query
            top_k: Number of chunks to retrieve

        Returns:
            Tuple of (answer, metadata)
        """
        # Retrieve relevant chunks
        chunks = self.retrieve(query, top_k=top_k)

        if not chunks:
            return "I couldn't find relevant information to answer your question.", {
                "query": query,
                "chunks_found": 0,
                "sources": []
            }

        # Generate answer
        answer = self.generate_answer(query, chunks)

        # Prepare metadata
        metadata = {
            "query": query,
            "chunks_found": len(chunks),
            "sources": list(set(chunk["source"] for chunk in chunks)),
            "top_scores": [chunk["score"] for chunk in chunks]
        }

        return answer, metadata


def rag_answer(query: str, top_k: int = 5, collection_name: str = "documents") -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function for quick RAG queries.

    Args:
        query: User query
        top_k: Number of chunks to retrieve
        collection_name: ChromaDB collection name (default: "documents")

    Returns:
        Tuple of (answer, metadata)
    """
    agent = SimpleRagAgent(collection_name=collection_name)
    return agent.answer_query(query, top_k=top_k)


if __name__ == "__main__":
    import sys

    # Example usage
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "What is this document about?"

    print("\n" + "="*60)
    print(f"Query: {query}")
    print("="*60 + "\n")

    try:
        agent = SimpleRagAgent()
        answer, metadata = agent.answer_query(query)

        print("Answer:")
        print(answer)
        print("\n" + "-"*60)
        print(f"Sources: {', '.join(metadata['sources'])}")
        print(f"Chunks retrieved: {metadata['chunks_found']}")
        print("="*60)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease build the knowledge base first:")
        print("  python -m rag_agent.build_kb_simple")
    except Exception as e:
        print(f"Error: {e}")
