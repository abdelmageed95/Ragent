"""
Local Embedding Generation Module

This module provides local, cost-free embedding generation using:
- Sentence Transformers for text embeddings
- CLIP for multimodal (text + image) embeddings

Benefits over Cohere API:
- Zero API costs
- 10-100x faster (no network latency)
- Unlimited usage (no rate limits)
- Better privacy (data stays local)
- GPU acceleration support
- Offline capability
"""

import os
import logging
from typing import Union, List, Optional
import numpy as np
from pathlib import Path

try:
    import torch
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning(
        "Sentence Transformers not installed. Install with:\n"
        "pip install sentence-transformers torch"
    )

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalEmbeddingManager:
    """
    Manager for local embedding generation using Sentence Transformers and CLIP.

    Features:
    - Text embeddings with Sentence Transformers
    - Image embeddings with CLIP
    - Automatic GPU detection and utilization
    - Model caching for performance
    - Batch processing support
    - L2 normalization for cosine similarity
    """

    # Model recommendations
    TEXT_MODELS = {
        'fast': 'sentence-transformers/all-MiniLM-L6-v2',      # 384 dims, fastest
        'balanced': 'sentence-transformers/all-mpnet-base-v2',  # 768 dims, best quality
        'qa': 'sentence-transformers/multi-qa-mpnet-base-dot-v1',  # Optimized for Q&A
        'multilingual': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
    }

    CLIP_MODELS = {
        'fast': 'sentence-transformers/clip-ViT-B-32',         # 512 dims, fastest
        'balanced': 'sentence-transformers/clip-ViT-B-16',     # 512 dims, better quality
        'best': 'sentence-transformers/clip-ViT-L-14'          # 768 dims, best quality
    }

    _instances = {}  # Cache for model instances

    def __init__(
        self,
        text_model: str = 'balanced',
        image_model: str = 'balanced',
        device: Optional[str] = None,
        cache_folder: Optional[str] = None
    ):
        """
        Initialize the local embedding manager.

        Args:
            text_model: Model for text embeddings ('fast', 'balanced', 'qa', 'multilingual')
                       or full model name
            image_model: Model for image embeddings ('fast', 'balanced', 'best')
                        or full model name
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            cache_folder: Folder to cache downloaded models
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Sentence Transformers not installed. Install with:\n"
                "pip install sentence-transformers torch"
            )

        # Resolve model names
        self.text_model_name = self.TEXT_MODELS.get(text_model, text_model)
        self.image_model_name = self.CLIP_MODELS.get(image_model, image_model)

        # Detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        # Set cache folder
        self.cache_folder = cache_folder or os.path.join(
            Path.home(), '.cache', 'sentence_transformers'
        )

        # Initialize models (lazy loading)
        self._text_model = None
        self._image_model = None

        logger.info("LocalEmbeddingManager initialized")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Text model: {self.text_model_name}")
        logger.info(f"  Image model: {self.image_model_name}")

        if self.device == 'cuda':
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"  GPU: {gpu_name}")

    @property
    def text_model(self) -> SentenceTransformer:
        """Lazy load text model"""
        if self._text_model is None:
            logger.info(f"Loading text model: {self.text_model_name}...")
            self._text_model = SentenceTransformer(
                self.text_model_name,
                device=self.device,
                cache_folder=self.cache_folder
            )
            logger.info(f"✓ Text model loaded ({self.text_embedding_dim} dims)")
        return self._text_model

    @property
    def image_model(self) -> SentenceTransformer:
        """Lazy load image model (CLIP)"""
        if self._image_model is None:
            logger.info(f"Loading image model: {self.image_model_name}...")
            self._image_model = SentenceTransformer(
                self.image_model_name,
                device=self.device,
                cache_folder=self.cache_folder
            )
            logger.info(f"✓ Image model loaded ({self.image_embedding_dim} dims)")
        return self._image_model

    @property
    def text_embedding_dim(self) -> int:
        """Get text embedding dimension"""
        return self.text_model.get_sentence_embedding_dimension()

    @property
    def image_embedding_dim(self) -> int:
        """Get image embedding dimension"""
        return self.image_model.get_sentence_embedding_dimension()

    def embed_text(
        self,
        text: Union[str, List[str]],
        normalize: bool = True,
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for text using Sentence Transformers.

        Args:
            text: Single text string or list of texts
            normalize: Apply L2 normalization (for cosine similarity)
            batch_size: Batch size for processing multiple texts
            show_progress: Show progress bar for batch processing

        Returns:
            Numpy array of embeddings (1D for single text, 2D for list)
        """
        # Convert single text to list
        is_single = isinstance(text, str)
        if is_single:
            text = [text]

        # Generate embeddings
        embeddings = self.text_model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=show_progress
        )

        # Return single embedding or array
        return embeddings[0] if is_single else embeddings

    def embed_image(
        self,
        image: Union[Image.Image, List[Image.Image], str, List[str]],
        normalize: bool = True,
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for images using CLIP.

        Args:
            image: PIL Image, list of images, image path, or list of paths
            normalize: Apply L2 normalization (for cosine similarity)
            batch_size: Batch size for processing multiple images
            show_progress: Show progress bar for batch processing

        Returns:
            Numpy array of embeddings (1D for single image, 2D for list)
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL not available. Install with: pip install Pillow")

        # Handle different input types
        is_single = not isinstance(image, list)

        if isinstance(image, str):
            # Single path
            image = Image.open(image)
        elif isinstance(image, list) and image and isinstance(image[0], str):
            # List of paths
            image = [Image.open(p) for p in image]

        if is_single:
            image = [image]

        # Generate embeddings
        embeddings = self.image_model.encode(
            image,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=show_progress
        )

        # Return single embedding or array
        return embeddings[0] if is_single else embeddings

    def embed_query(
        self,
        query: str,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embedding for a search query (optimized for retrieval).

        Args:
            query: Query text
            normalize: Apply L2 normalization

        Returns:
            Numpy array embedding
        """
        return self.embed_text(query, normalize=normalize)

    def embed_documents(
        self,
        documents: List[str],
        normalize: bool = True,
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple documents (optimized for indexing).

        Args:
            documents: List of document texts
            normalize: Apply L2 normalization
            batch_size: Batch size for processing
            show_progress: Show progress bar

        Returns:
            2D numpy array of embeddings
        """
        return self.embed_text(
            documents,
            normalize=normalize,
            batch_size=batch_size,
            show_progress=show_progress
        )

    @staticmethod
    def l2_normalize(vec: np.ndarray) -> np.ndarray:
        """
        Apply L2 normalization to vector(s).

        Args:
            vec: 1D or 2D numpy array

        Returns:
            Normalized array
        """
        if vec.ndim == 1:
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        else:
            # Batch normalization
            norms = np.linalg.norm(vec, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            return vec / norms

    def get_model_info(self) -> dict:
        """
        Get information about loaded models.

        Returns:
            Dictionary with model information
        """
        info = {
            'device': self.device,
            'text_model': {
                'name': self.text_model_name,
                'loaded': self._text_model is not None,
                'dimension': self.text_embedding_dim if self._text_model else None
            },
            'image_model': {
                'name': self.image_model_name,
                'loaded': self._image_model is not None,
                'dimension': self.image_embedding_dim if self._image_model else None
            }
        }

        if self.device == 'cuda':
            info['gpu'] = {
                'name': torch.cuda.get_device_name(0),
                'memory_allocated': f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
                'memory_reserved': f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB"
            }

        return info

    @classmethod
    def get_instance(
        cls,
        text_model: str = 'balanced',
        image_model: str = 'balanced',
        **kwargs
    ) -> 'LocalEmbeddingManager':
        """
        Get or create a singleton instance (for model caching).

        Args:
            text_model: Text model name
            image_model: Image model name
            **kwargs: Additional arguments for initialization

        Returns:
            LocalEmbeddingManager instance
        """
        key = (text_model, image_model)
        if key not in cls._instances:
            cls._instances[key] = cls(text_model, image_model, **kwargs)
        return cls._instances[key]

    def clear_cache(self):
        """Clear model cache and free GPU memory"""
        if self._text_model is not None:
            del self._text_model
            self._text_model = None

        if self._image_model is not None:
            del self._image_model
            self._image_model = None

        if self.device == 'cuda':
            torch.cuda.empty_cache()

        logger.info("Model cache cleared")


# Global instance (lazy initialization)
_global_manager: Optional[LocalEmbeddingManager] = None


def get_embedding_manager(
    text_model: str = 'balanced',
    image_model: str = 'balanced',
    force_new: bool = False
) -> LocalEmbeddingManager:
    """
    Get the global embedding manager instance.

    Args:
        text_model: Text model preset or name
        image_model: Image model preset or name
        force_new: Force creation of new instance

    Returns:
        LocalEmbeddingManager instance
    """
    global _global_manager

    if force_new or _global_manager is None:
        _global_manager = LocalEmbeddingManager(text_model, image_model)

    return _global_manager


# Convenience functions (compatible with embedding_helpers.py interface)
def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """
    Generate text embedding (convenience function).

    Args:
        text: Text to embed
        normalize: Apply L2 normalization

    Returns:
        Numpy array embedding
    """
    manager = get_embedding_manager()
    return manager.embed_text(text, normalize=normalize)


def embed_image(image: Union[Image.Image, str], normalize: bool = True) -> np.ndarray:
    """
    Generate image embedding (convenience function).

    Args:
        image: PIL Image or image path
        normalize: Apply L2 normalization

    Returns:
        Numpy array embedding
    """
    manager = get_embedding_manager()
    return manager.embed_image(image, normalize=normalize)


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    """
    L2 normalize vector(s) (convenience function).

    Args:
        vec: Vector or array of vectors

    Returns:
        Normalized array
    """
    return LocalEmbeddingManager.l2_normalize(vec)


# Comparison with Cohere
def compare_with_cohere(sample_text: str = "This is a test."):
    """
    Compare local embeddings with Cohere (if available).

    Args:
        sample_text: Text to use for comparison
    """
    print("\n" + "="*60)
    print("  Embedding Comparison: Local vs Cohere")
    print("="*60)

    # Local embeddings
    print("\n1. Local Embeddings (Sentence Transformers)")
    import time

    manager = get_embedding_manager()

    start = time.time()
    local_emb = manager.embed_text(sample_text)
    local_time = time.time() - start

    print(f"   Model: {manager.text_model_name}")
    print(f"   Dimension: {len(local_emb)}")
    print(f"   Time: {local_time*1000:.2f}ms")
    print(f"   Sample: {local_emb[:5]}")

    # Cohere (if available)
    try:
        import cohere
        print("\n2. Cohere Embeddings (API)")

        co_client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

        start = time.time()
        resp = co_client.embed(
            model="embed-v4.0",
            input_type="search_document",
            embedding_types=["float"],
            texts=[sample_text],
        )
        cohere_emb = np.array(resp.embeddings.float[0], dtype=np.float32)
        cohere_time = time.time() - start

        print(f"   Model: embed-v4.0")
        print(f"   Dimension: {len(cohere_emb)}")
        print(f"   Time: {cohere_time*1000:.2f}ms")
        print(f"   Sample: {cohere_emb[:5]}")

        # Comparison
        print("\n3. Comparison")
        speedup = cohere_time / local_time
        print(f"   Speedup: {speedup:.1f}x faster")
        print(f"   Cost: Local = $0, Cohere = $0.0001+ per request")

    except Exception as e:
        print(f"\n2. Cohere not available: {e}")

    print("="*60)


if __name__ == "__main__":
    # Example usage
    print("Testing Local Embedding Manager...")

    # Initialize manager
    manager = LocalEmbeddingManager(text_model='balanced', image_model='balanced')

    # Text embedding
    text = "This is a sample document about machine learning."
    text_emb = manager.embed_text(text)
    print(f"\nText embedding shape: {text_emb.shape}")

    # Batch text embedding
    texts = ["Document 1", "Document 2", "Document 3"]
    batch_emb = manager.embed_documents(texts)
    print(f"Batch embedding shape: {batch_emb.shape}")

    # Model info
    print("\nModel Info:")
    import json
    print(json.dumps(manager.get_model_info(), indent=2))

    # Comparison
    compare_with_cohere()
