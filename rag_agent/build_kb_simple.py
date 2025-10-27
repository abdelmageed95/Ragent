"""
Simple Knowledge Base Builder

Builds a ChromaDB collection from PDF documents using text-only processing.
No image processing, no Docling, just straightforward text extraction and embedding.
"""

import os
import uuid
import hashlib
import logging
from typing import List, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

from rag_agent.pdf_extractor import SimplePDFExtractor
from rag_agent.embedding_helpers import embed_text

# Load environment variables
load_dotenv()

# Directory to save ChromaDB database
DATA_DIR = "data"
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file's content.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def check_duplicate_document(collection, file_hash: str) -> Optional[str]:
    """
    Check if a document with the given hash already exists in the collection.

    Args:
        collection: ChromaDB collection
        file_hash: SHA256 hash of the file

    Returns:
        Document ID if duplicate found, None otherwise
    """
    try:
        # Query collection for documents with this hash
        results = collection.get(
            where={"file_hash": file_hash},
            limit=1
        )

        if results and results['ids']:
            # Extract doc_id from the first chunk ID (format: doc_id_chunk_0)
            chunk_id = results['ids'][0]
            doc_id = chunk_id.rsplit('_chunk_', 1)[0]
            return doc_id

        return None
    except Exception as e:
        logger.warning(f"Error checking for duplicates: {e}")
        return None


def build_text_index(
    pdf_paths: List[str],
    collection_name: str = "documents",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    reset_collection: bool = False
) -> dict:
    """
    Build a ChromaDB collection for text chunks from PDF documents.

    Simple pipeline:
    1. Extract text from PDFs
    2. Chunk text into smaller pieces
    3. Generate embeddings for each chunk
    4. Store in ChromaDB collection (embeddings + metadata together)

    Args:
        pdf_paths: List of PDF file paths to process
        collection_name: Name of the ChromaDB collection
        chunk_size: Words per chunk
        chunk_overlap: Overlapping words between chunks
        reset_collection: If True, delete existing collection before building

    Returns:
        Dictionary with build summary including duplicate information
    """
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    # Get or create collection
    if reset_collection:
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Simple text-only RAG knowledge base"}
    )

    logger.info(f"Using ChromaDB collection: {collection_name}")
    logger.info(f"Processing {len(pdf_paths)} PDF files...")

    extractor = SimplePDFExtractor()
    total_chunks = 0
    skipped_duplicates = 0
    duplicate_files = []  # Track duplicate filenames

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            continue

        filename = os.path.basename(pdf_path)
        doc_id = str(uuid.uuid4())

        logger.info(f"\nProcessing: {filename}")

        try:
            # Calculate file hash for duplicate detection
            file_hash = calculate_file_hash(pdf_path)
            logger.info(f"  File hash: {file_hash[:16]}...")

            # Check if document already exists
            existing_doc_id = check_duplicate_document(collection, file_hash)
            if existing_doc_id:
                logger.warning(f"  ⚠️  DUPLICATE DETECTED - Skipping {filename}")
                logger.info(f"      This file already exists in the collection (doc_id: {existing_doc_id[:16]}...)")
                skipped_duplicates += 1
                duplicate_files.append(filename)
                continue

            # Extract text
            text = extractor.extract_text(pdf_path)

            if not text or len(text.strip()) < 100:
                logger.warning(f"  Skipping {filename} - insufficient text content")
                continue

            # Chunk text
            chunks = extractor.chunk_text(text, chunk_size, chunk_overlap)
            logger.info(f"  Created {len(chunks)} chunks")

            # Prepare batch data for ChromaDB
            chunk_ids = []
            chunk_texts = []
            chunk_embeddings = []
            chunk_metadata = []

            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                try:
                    vec = embed_text(chunk)

                    chunk_ids.append(f"{doc_id}_chunk_{i}")
                    chunk_texts.append(chunk)
                    chunk_embeddings.append(vec.tolist())
                    chunk_metadata.append({
                        "source": filename,
                        "chunk_index": i,
                        "pdf_path": pdf_path,
                        "doc_id": doc_id,
                        "file_hash": file_hash  # Store hash for duplicate detection
                    })

                    if (i + 1) % 10 == 0:
                        logger.info(f"  Embedded {i + 1}/{len(chunks)} chunks")

                except Exception as e:
                    logger.error(f"  Failed to embed chunk {i}: {e}")

            # Add all chunks to ChromaDB in batch
            if chunk_ids:
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_texts,
                    embeddings=chunk_embeddings,
                    metadatas=chunk_metadata
                )
                total_chunks += len(chunk_ids)
                logger.info(f"  Added {len(chunk_ids)} chunks to collection")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            continue

    logger.info("\n" + "="*60)
    logger.info("Knowledge base build complete!")
    logger.info(f"  Collection: {collection_name}")
    logger.info(f"  Location: {CHROMA_DB_DIR}")
    logger.info(f"  Total files submitted: {len(pdf_paths)}")
    logger.info(f"  Duplicates skipped: {skipped_duplicates}")
    logger.info(f"  New documents added: {len(pdf_paths) - skipped_duplicates}")
    logger.info(f"  New chunks added: {total_chunks}")
    logger.info(f"  Total collection count: {collection.count()}")
    logger.info("="*60)

    # Return summary
    return {
        "total_files": len(pdf_paths),
        "duplicates_skipped": skipped_duplicates,
        "duplicate_files": duplicate_files,
        "new_documents": len(pdf_paths) - skipped_duplicates,
        "new_chunks": total_chunks,
        "collection_total": collection.count()
    }


if __name__ == "__main__":
    # Example usage
    pdf_folder = "./pdfs"

    if os.path.exists(pdf_folder):
        pdf_files = [
            os.path.join(pdf_folder, f)
            for f in os.listdir(pdf_folder)
            if f.endswith(".pdf")
        ]

        if pdf_files:
            logger.info(f"Found {len(pdf_files)} PDF files in {pdf_folder}")
            build_text_index(
                pdf_files,
                chunk_size=500,
                chunk_overlap=50
            )
        else:
            logger.warning(f"No PDF files found in {pdf_folder}")
    else:
        logger.error(f"PDF folder not found: {pdf_folder}")
        logger.info("Create a 'pdfs' folder and add PDF files to get started.")
