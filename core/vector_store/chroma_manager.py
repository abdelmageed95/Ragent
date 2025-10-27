"""
ChromaDB Singleton Manager

Manages a single ChromaDB client instance across the application to prevent
"An instance of Chroma already exists for data/chroma_db with different settings" errors.

This singleton pattern ensures:
1. Only one ChromaDB PersistentClient is created per database path
2. Consistent settings across all ChromaDB operations
3. Thread-safe access to collections
4. Proper resource management and cleanup
"""

import os
import threading
from typing import Dict, Optional
import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection


class ChromaDBManager:
    """
    Singleton manager for ChromaDB clients.

    Ensures only one PersistentClient exists per database path,
    preventing configuration conflicts.
    """

    _instances: Dict[str, chromadb.PersistentClient] = {}
    _lock = threading.Lock()

    @classmethod
    def get_client(
        cls,
        db_path: str,
        settings: Optional[Settings] = None
    ) -> chromadb.PersistentClient:
        """
        Get or create a ChromaDB client for the specified path.

        Args:
            db_path: Path to ChromaDB database directory
            settings: ChromaDB settings (only used on first creation)

        Returns:
            ChromaDB PersistentClient instance
        """
        # Normalize path to avoid duplicate instances
        db_path = os.path.abspath(db_path)

        # Check if client already exists
        if db_path in cls._instances:
            return cls._instances[db_path]

        # Thread-safe client creation
        with cls._lock:
            # Double-check after acquiring lock
            if db_path in cls._instances:
                return cls._instances[db_path]

            # Create database directory if needed
            os.makedirs(db_path, exist_ok=True)

            # Use provided settings or defaults
            if settings is None:
                settings = Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )

            # Create new client
            client = chromadb.PersistentClient(
                path=db_path,
                settings=settings
            )

            # Cache the client
            cls._instances[db_path] = client

            print(f"✅ ChromaDB: Created new client for {db_path}")
            return client

    @classmethod
    def get_or_create_collection(
        cls,
        db_path: str,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> Collection:
        """
        Get or create a collection in the specified database.

        Args:
            db_path: Path to ChromaDB database directory
            collection_name: Name of the collection
            metadata: Optional metadata for the collection

        Returns:
            ChromaDB Collection instance
        """
        client = cls.get_client(db_path)

        # Get or create collection
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {}
        )

        return collection

    @classmethod
    def reset_client(cls, db_path: str) -> None:
        """
        Reset (remove) the cached client for a database path.

        Use this when you need to recreate a client with different settings.

        Args:
            db_path: Path to ChromaDB database directory
        """
        db_path = os.path.abspath(db_path)

        with cls._lock:
            if db_path in cls._instances:
                del cls._instances[db_path]
                print(f"🔄 ChromaDB: Reset client for {db_path}")

    @classmethod
    def reset_all(cls) -> None:
        """
        Reset all cached clients.

        Use this for testing or application shutdown.
        """
        with cls._lock:
            cls._instances.clear()
            print("🔄 ChromaDB: Reset all clients")

    @classmethod
    def list_collections(cls, db_path: str) -> list:
        """
        List all collections in a database.

        Args:
            db_path: Path to ChromaDB database directory

        Returns:
            List of collection names
        """
        client = cls.get_client(db_path)
        collections = client.list_collections()
        return [col.name for col in collections]

    @classmethod
    def delete_collection(
        cls,
        db_path: str,
        collection_name: str
    ) -> None:
        """
        Delete a collection from the database.

        Args:
            db_path: Path to ChromaDB database directory
            collection_name: Name of the collection to delete
        """
        client = cls.get_client(db_path)
        try:
            client.delete_collection(collection_name)
            print(f"🗑️  ChromaDB: Deleted collection '{collection_name}'")
        except ValueError:
            print(f"⚠️  ChromaDB: Collection '{collection_name}' not found")


# Convenience functions for common operations

def get_chroma_client(db_path: str = "data/chroma_db") -> chromadb.PersistentClient:
    """
    Get ChromaDB client for the default or specified path.

    Args:
        db_path: Path to ChromaDB database directory

    Returns:
        ChromaDB PersistentClient instance
    """
    return ChromaDBManager.get_client(db_path)


def get_chroma_collection(
    collection_name: str,
    db_path: str = "data/chroma_db",
    metadata: Optional[Dict] = None
) -> Collection:
    """
    Get or create a ChromaDB collection.

    Args:
        collection_name: Name of the collection
        db_path: Path to ChromaDB database directory
        metadata: Optional metadata for the collection

    Returns:
        ChromaDB Collection instance
    """
    return ChromaDBManager.get_or_create_collection(
        db_path=db_path,
        collection_name=collection_name,
        metadata=metadata
    )


# Example usage:
if __name__ == "__main__":
    # Example 1: Get client
    client = get_chroma_client("data/chroma_db")
    print(f"Client: {client}")

    # Example 2: Get collection
    collection = get_chroma_collection(
        collection_name="documents",
        metadata={"description": "RAG documents"}
    )
    print(f"Collection: {collection.name}, Count: {collection.count()}")

    # Example 3: List collections
    collections = ChromaDBManager.list_collections("data/chroma_db")
    print(f"Collections: {collections}")

    # Example 4: Multiple clients with same path (returns cached instance)
    client2 = get_chroma_client("data/chroma_db")
    print(f"Same client? {client is client2}")  # Should be True
