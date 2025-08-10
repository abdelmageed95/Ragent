import os
import faiss
import pickle

data_dir = "data"
os.makedirs(data_dir, exist_ok=True)

def load_indices(
    text_index_path: str = os.path.join(data_dir, "faiss_text.index"),
    image_index_path: str = os.path.join(data_dir, "faiss_image.index"),
    text_meta_path: str = os.path.join(data_dir, "text_docs_info.pkl"),
    image_meta_path: str = os.path.join(data_dir, "image_docs_info.pkl"),
):
    """Return (idx_text, text_meta, idx_img, image_meta)."""
    print(f"Loading indices from {text_index_path} and {image_index_path}"
          f" with metadata from {text_meta_path} and {image_meta_path}")
    idx_text, text_meta = None, []
    idx_img, image_meta = None, []
    try:
        if os.path.exists(text_index_path) and os.path.exists(text_meta_path):
            idx_text = faiss.read_index(text_index_path)
            with open(text_meta_path, "rb") as f:
                text_meta = pickle.load(f)
    except Exception as e:
        print(f"Error loading text index: {e}")

    try:
        if os.path.exists(image_index_path) and os.path.exists(image_meta_path):
            idx_img = faiss.read_index(image_index_path)
            with open(image_meta_path, "rb") as f:
                image_meta = pickle.load(f)
    except Exception as e:
        print(f"Error loading image index: {e}")

    return idx_text, text_meta, idx_img, image_meta

