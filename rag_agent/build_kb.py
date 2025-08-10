import os
import pickle
import uuid
from typing import List

import faiss
import numpy as np
import pdf2image
import PyPDF2
from PIL import Image
import cohere
import logging
from dotenv import load_dotenv

from rag_agent.embedding_helpers import embed_text, embed_image

# Load environment variables
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
# Directory to save indices, metadata, and image previews
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)

# Cohere client initialization
co_client = cohere.ClientV2(api_key=COHERE_API_KEY)

# Text Chunking
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split a long text into overlapping chunks of approximately `chunk_size` words.
    """
    words = text.split()
    chunks = []
    start = 0
    logging.info("Chunking text into size %d with overlap %d", chunk_size, overlap)
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

# PDF Handling
def pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """
    Convert each page of a PDF file to a PIL Image.
    """
    return pdf2image.convert_from_path(pdf_path, dpi=200)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract raw text from a PDF using PyPDF2.
    """
    texts = []
    logging.info("Extracting text from %s", pdf_path)
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                texts.append(txt)
    return "\n".join(texts)

# Index Building             

def build_and_save_indices(
    pdf_paths: List[str],
    text_index_path: str = os.path.join(data_dir, "faiss_text.index"),
    image_index_path: str = os.path.join(data_dir, "faiss_image.index"),
    text_meta_path: str = os.path.join(data_dir, "text_docs_info.pkl"),
    image_meta_path: str = os.path.join(data_dir, "image_docs_info.pkl"),
) -> None:
    """
    Build FAISS indices for text chunks and image pages, saving metadata. Each image preview is
    saved to disk so it can later be passed to the LLM context.
    """
    text_vectors, image_vectors = [], []
    text_meta, image_meta = [], []

    for pdf_path in pdf_paths:
        uid = str(uuid.uuid4())
        filename = os.path.basename(pdf_path)

        # --- Text chunks ---
        raw_text = extract_text_from_pdf(pdf_path)
        for i, chunk in enumerate(chunk_text(raw_text)):
            vec = embed_text(chunk)
            text_vectors.append(vec)
            text_meta.append({
                "doc_id": f"{uid}_txt_{i}",
                "source": filename,
                "chunk": i,
                "content": chunk,
            })

        # --- Image pages ---
        for page_num, img in enumerate(pdf_to_images(pdf_path), start=1):
            vec = embed_image(img)
            image_vectors.append(vec)
            # Save a preview image to disk
            preview_fname = f"{uid}_img_{page_num}.png"
            preview_path = os.path.join(data_dir, preview_fname)
            img.save(preview_path)

            image_meta.append({
                "doc_id": f"{uid}_img_{page_num}",
                "source": filename,
                "page": page_num,
                "preview_image": preview_path,
            })

    # --- Persist FAISS indices and metadata ---
    if text_vectors:
        dim = text_vectors[0].shape[0]
        idx_t = faiss.IndexFlatIP(dim)
        idx_t.add(np.vstack(text_vectors))
        faiss.write_index(idx_t, text_index_path)
        with open(text_meta_path, "wb") as f:
            pickle.dump(text_meta, f)
        logging.info("Saved text index with %d vectors", len(text_vectors))

    if image_vectors:
        dim = image_vectors[0].shape[0]
        idx_i = faiss.IndexFlatIP(dim)
        idx_i.add(np.vstack(image_vectors))
        faiss.write_index(idx_i, image_index_path)
        with open(image_meta_path, "wb") as f:
            pickle.dump(image_meta, f)
        logging.info("Saved image index with %d vectors", len(image_vectors))

# Example usage:
# if __name__ == "__main__":
#     # pdf_folder = "./pdfs"
      # pdf_files = [os.path.join(pdf_folder, f) for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
      # build_and_save_indices(pdf_files)
