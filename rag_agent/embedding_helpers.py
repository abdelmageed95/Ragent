import os
import io
import numpy as np
from PIL import Image
import cohere
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
# Cohere client initialization
co_client = cohere.ClientV2(api_key=COHERE_API_KEY)



#--------------------------
# Embedding Helpers
# --------------------------
def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed_text(text: str) -> np.ndarray:
    """
    Get a normalized text embedding via Cohere embed-v4.0
    """
    resp = co_client.embed(
        model="embed-v4.0",
        input_type="search_document",
        embedding_types=["float"],
        texts=[text],
    )
    vec = np.array(resp.embeddings.float[0], dtype=np.float32)
    return l2_normalize(vec)


def embed_image(img: Image.Image) -> np.ndarray:
    """
    Get a normalized image embedding via Cohere embed-v4.0
    """
    # Resize if too large
    MAX_PIXELS = 1568 * 1568
    if img.width * img.height > MAX_PIXELS:
        scale = (MAX_PIXELS / (img.width * img.height)) ** 0.5
        img = img.resize((int(img.width * scale), int(img.height * scale)))

    # Convert to data URI
    import base64
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
