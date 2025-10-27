"""
Embedding Helpers Module

This module provides embedding generation functions with support for both:
- Local embeddings (Sentence Transformers + CLIP) - FREE, FAST, UNLIMITED
- Cohere API embeddings (legacy fallback)

Configuration via environment variable:
- USE_LOCAL_EMBEDDINGS=true  -> Use local models (default, recommended)
- USE_LOCAL_EMBEDDINGS=false -> Use Cohere API (costs money)
"""

import os
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check configuration
USE_LOCAL_EMBEDDINGS = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"

# Try importing local embeddings
try:
    from rag_agent.local_embeddings import (
        LocalEmbeddingManager,
        get_embedding_manager
    )
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False
    logger.warning(
        "Local embeddings not available. Install with:\n"
        "pip install sentence-transformers torch"
    )

# Try importing Cohere
try:
    import cohere
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    if COHERE_API_KEY:
        co_client = cohere.ClientV2(api_key=COHERE_API_KEY)
        COHERE_AVAILABLE = True
    else:
        COHERE_AVAILABLE = False
        logger.warning("COHERE_API_KEY not found in environment")
except ImportError:
    COHERE_AVAILABLE = False
    logger.warning("Cohere not installed")

# Determine which backend to use
if USE_LOCAL_EMBEDDINGS and LOCAL_EMBEDDINGS_AVAILABLE:
    EMBEDDING_BACKEND = "local"
    logger.info("✓ Using LOCAL embeddings (Sentence Transformers + CLIP)")
    logger.info("  Benefits: $0 cost, 10-100x faster, unlimited usage")
elif COHERE_AVAILABLE:
    EMBEDDING_BACKEND = "cohere"
    logger.warning("⚠ Using COHERE API embeddings (costs money)")
    logger.warning("  Consider switching to local embeddings for free unlimited usage")
else:
    EMBEDDING_BACKEND = None
    logger.error("✗ No embedding backend available!")
    raise RuntimeError(
        "No embedding backend available. Install local embeddings with:\n"
        "pip install sentence-transformers torch"
    )


#--------------------------
# Helper Functions
# --------------------------

def l2_normalize(vec: np.ndarray) -> np.ndarray:
    """
    L2 normalize vector or array of vectors.

    Args:
        vec: 1D or 2D numpy array

    Returns:
        Normalized array
    """
    if vec.ndim == 1:
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    else:
        norms = np.linalg.norm(vec, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return vec / norms


#--------------------------
# Local Embedding Functions
# --------------------------

def _embed_text_local(text: str) -> np.ndarray:
    """Generate text embedding using local Sentence Transformers"""
    manager = get_embedding_manager()
    return manager.embed_text(text, normalize=True)


def _embed_image_local(img: Image.Image) -> np.ndarray:
    """Generate image embedding using local CLIP"""
    manager = get_embedding_manager()
    return manager.embed_image(img, normalize=True)


#--------------------------
# Cohere Embedding Functions (Legacy)
# --------------------------

def _embed_text_cohere(text: str) -> np.ndarray:
    """Generate text embedding using Cohere API"""
    try:
        resp = co_client.embed(
            model="embed-v4.0",
            input_type="search_document",
            embedding_types=["float"],
            texts=[text],
        )
        vec = np.array(resp.embeddings.float[0], dtype=np.float32)
        return l2_normalize(vec)
    except Exception as e:
        logger.error(f"Cohere text embedding failed: {e}")
        raise


def _embed_image_cohere(img: Image.Image) -> np.ndarray:
    """Generate image embedding using Cohere API"""
    import io
    import base64

    try:
        # Resize if too large
        MAX_PIXELS = 1568 * 1568
        if img.width * img.height > MAX_PIXELS:
            scale = (MAX_PIXELS / (img.width * img.height)) ** 0.5
            img = img.resize((int(img.width * scale), int(img.height * scale)))

        # Convert to data URI
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        data_uri = f"data:image/png;base64,{b64}"

        resp = co_client.embed(
            model="embed-v4.0",
            input_type="search_document",
            embedding_types=["float"],
            inputs=[{"content": [{"type": "image", "image": data_uri}]}],
        )
        vec = np.array(resp.embeddings.float[0], dtype=np.float32)
        return l2_normalize(vec)
    except Exception as e:
        logger.error(f"Cohere image embedding failed: {e}")
        raise


#--------------------------
# Public API
# --------------------------

def embed_text(text: str) -> np.ndarray:
    """
    Generate text embedding using the configured backend.

    Args:
        text: Text to embed

    Returns:
        Normalized numpy array embedding

    Raises:
        RuntimeError: If no backend is available
    """
    if EMBEDDING_BACKEND == "local":
        return _embed_text_local(text)
    elif EMBEDDING_BACKEND == "cohere":
        return _embed_text_cohere(text)
    else:
        raise RuntimeError("No embedding backend available")


def embed_image(img: Image.Image) -> np.ndarray:
    """
    Generate image embedding using the configured backend.

    Args:
        img: PIL Image to embed

    Returns:
        Normalized numpy array embedding

    Raises:
        RuntimeError: If no backend is available
    """
    if EMBEDDING_BACKEND == "local":
        return _embed_image_local(img)
    elif EMBEDDING_BACKEND == "cohere":
        return _embed_image_cohere(img)
    else:
        raise RuntimeError("No embedding backend available")


def get_embedding_info() -> dict:
    """
    Get information about the current embedding configuration.

    Returns:
        Dictionary with embedding configuration details
    """
    info = {
        "backend": EMBEDDING_BACKEND,
        "local_available": LOCAL_EMBEDDINGS_AVAILABLE,
        "cohere_available": COHERE_AVAILABLE,
        "use_local_embeddings": USE_LOCAL_EMBEDDINGS,
    }

    if EMBEDDING_BACKEND == "local":
        manager = get_embedding_manager()
        info["model_info"] = manager.get_model_info()
        info["cost"] = "$0 (free)"
        info["rate_limit"] = "unlimited"

    elif EMBEDDING_BACKEND == "cohere":
        info["model"] = "embed-v4.0"
        info["cost"] = "$0.0001+ per request"
        info["rate_limit"] = "API rate limits apply"

    return info


def switch_to_local_embeddings():
    """
    Switch to local embeddings (requires restart or re-import).

    This function updates the environment variable, but you need to
    restart your application or re-import this module for it to take effect.
    """
    os.environ["USE_LOCAL_EMBEDDINGS"] = "true"
    logger.info("Set USE_LOCAL_EMBEDDINGS=true")
    logger.info("Please restart your application for changes to take effect")


def switch_to_cohere_embeddings():
    """
    Switch to Cohere API embeddings (requires restart or re-import).

    This function updates the environment variable, but you need to
    restart your application or re-import this module for it to take effect.
    """
    os.environ["USE_LOCAL_EMBEDDINGS"] = "false"
    logger.info("Set USE_LOCAL_EMBEDDINGS=false")
    logger.info("Please restart your application for changes to take effect")


# Print configuration on import
if __name__ != "__main__":
    logger.info(f"Embedding backend: {EMBEDDING_BACKEND}")


# Example usage and testing
if __name__ == "__main__":
    import json

    print("\n" + "="*60)
    print("  Embedding Configuration")
    print("="*60)

    info = get_embedding_info()
    print(json.dumps(info, indent=2))

    print("\n" + "="*60)
    print("  Testing Embeddings")
    print("="*60)

    # Test text embedding
    print("\nTesting text embedding...")
    text = "This is a test document about machine learning."
    text_emb = embed_text(text)
    print(f"✓ Text embedding shape: {text_emb.shape}")
    print(f"  Sample values: {text_emb[:5]}")

    # Test image embedding (if PIL available)
    try:
        print("\nTesting image embedding...")
        # Create a test image
        test_img = Image.new('RGB', (224, 224), color='blue')
        img_emb = embed_image(test_img)
        print(f"✓ Image embedding shape: {img_emb.shape}")
        print(f"  Sample values: {img_emb[:5]}")
    except Exception as e:
        print(f"✗ Image embedding failed: {e}")

    print("\n" + "="*60)
    print("  Cost Comparison")
    print("="*60)

    if EMBEDDING_BACKEND == "local":
        print("\n✓ Using LOCAL embeddings")
        print("  - Cost: $0 (FREE)")
        print("  - Speed: 10-100x faster than API")
        print("  - Limit: Unlimited")
        print("  - Privacy: Data stays on your machine")
    else:
        print("\n⚠ Using COHERE API")
        print("  - Cost: ~$0.0001 per embedding")
        print("  - Speed: Network latency + processing")
        print("  - Limit: API rate limits apply")
        print("  - Privacy: Data sent to Cohere servers")
        print("\n  💡 Switch to local embeddings to save costs!")
        print("     pip install sentence-transformers torch")
        print("     export USE_LOCAL_EMBEDDINGS=true")

    print("="*60)
