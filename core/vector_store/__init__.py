"""
Vector Store Module

Provides centralized ChromaDB management with singleton pattern.
"""

from .chroma_manager import (
    ChromaDBManager,
    get_chroma_client,
    get_chroma_collection
)

__all__ = [
    'ChromaDBManager',
    'get_chroma_client',
    'get_chroma_collection'
]
