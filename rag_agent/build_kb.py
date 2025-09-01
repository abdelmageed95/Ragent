import os
import pickle
import uuid
from typing import List, Set, Tuple

import faiss
import numpy as np
import pdf2image
import PyPDF2
from PIL import Image, ImageStat
import cohere
import logging
import fitz  # PyMuPDF for better PDF analysis
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

# Page Content Analysis
def has_visual_content(pdf_path: str, page_num: int) -> bool:
    """
    Analyze a PDF page to determine if it contains images, charts, or tables.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
    
    Returns:
        True if page has visual content (images, charts, tables), False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Check for images
        image_list = page.get_images()
        if len(image_list) > 0:
            doc.close()
            return True
        
        # Check for drawings/vector graphics (charts, diagrams)
        drawings = page.get_drawings()
        if len(drawings) > 0:
            doc.close()
            return True
        
        # Check for tables by analyzing text blocks and their positioning
        text_blocks = page.get_text("dict")
        if _detect_table_structure(text_blocks):
            doc.close()
            return True
            
        doc.close()
        return False
        
    except Exception as e:
        logging.warning(f"Error analyzing page {page_num} in {pdf_path}: {e}")
        # If analysis fails, default to treating as visual content to be safe
        return True

def _detect_table_structure(text_dict: dict) -> bool:
    """
    Detect table-like structure by analyzing text block positions and alignment.
    """
    blocks = text_dict.get("blocks", [])
    if len(blocks) < 3:  # Need at least a few blocks for a table
        return False
    
    # Look for regular grid-like positioning
    y_positions = []
    x_positions = []
    
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                bbox = line["bbox"]
                y_positions.append(bbox[1])  # top y coordinate
                x_positions.append(bbox[0])  # left x coordinate
    
    # Check for multiple items at similar Y positions (table rows)
    y_groups = _group_similar_values(y_positions, tolerance=5)
    x_groups = _group_similar_values(x_positions, tolerance=10)
    
    # Table indicators: multiple rows and columns
    return len(y_groups) >= 3 and len(x_groups) >= 2

def _group_similar_values(values: List[float], tolerance: float) -> List[List[float]]:
    """Group values that are within tolerance of each other."""
    if not values:
        return []
    
    sorted_values = sorted(values)
    groups = []
    current_group = [sorted_values[0]]
    
    for val in sorted_values[1:]:
        if val - current_group[-1] <= tolerance:
            current_group.append(val)
        else:
            groups.append(current_group)
            current_group = [val]
    groups.append(current_group)
    
    # Only return groups with multiple items
    return [group for group in groups if len(group) >= 2]

def analyze_pdf_pages(pdf_path: str) -> Tuple[Set[int], Set[int]]:
    """
    Analyze all pages in a PDF to categorize them as text-only or visual content.
    
    Returns:
        Tuple of (text_only_pages, visual_pages) where page numbers are 0-indexed
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        text_only_pages = set()
        visual_pages = set()
        
        for page_num in range(total_pages):
            if has_visual_content(pdf_path, page_num):
                visual_pages.add(page_num)
            else:
                text_only_pages.add(page_num)
        
        logging.info(f"PDF {pdf_path}: {len(text_only_pages)} text-only pages, {len(visual_pages)} visual pages")
        return text_only_pages, visual_pages
        
    except Exception as e:
        logging.error(f"Error analyzing PDF {pdf_path}: {e}")
        # If analysis fails, process all pages as visual to be safe
        return set(), set(range(total_pages)) if 'total_pages' in locals() else set()

# PDF Handling
def pdf_to_images(pdf_path: str, page_numbers: Set[int] = None) -> List[Tuple[int, Image.Image]]:
    """
    Convert specific pages of a PDF file to PIL Images.
    
    Args:
        pdf_path: Path to PDF file
        page_numbers: Set of 0-indexed page numbers to convert. If None, converts all pages.
    
    Returns:
        List of (page_number, PIL_Image) tuples
    """
    if page_numbers is None:
        images = pdf2image.convert_from_path(pdf_path, dpi=200)
        return [(i, img) for i, img in enumerate(images)]
    else:
        # Convert only specific pages (pdf2image uses 1-indexed pages)
        pages_1indexed = [p + 1 for p in page_numbers]
        images = pdf2image.convert_from_path(pdf_path, dpi=200, first_page=min(pages_1indexed), last_page=max(pages_1indexed))
        
        # Filter to only requested pages
        result = []
        for i, page_1indexed in enumerate(sorted(pages_1indexed)):
            if i < len(images):
                result.append((page_1indexed - 1, images[i]))  # Convert back to 0-indexed
        return result

def extract_text_from_pdf(pdf_path: str, page_numbers: Set[int] = None) -> str:
    """
    Extract raw text from specific pages of a PDF using PyPDF2.
    
    Args:
        pdf_path: Path to PDF file
        page_numbers: Set of 0-indexed page numbers to extract text from. 
                     If None, extracts from all pages.
    
    Returns:
        Combined text from specified pages
    """
    texts = []
    logging.info("Extracting text from %s", pdf_path)
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            # Skip this page if we're only processing specific pages and 
            # this isn't one of them
            if page_numbers is not None and page_num not in page_numbers:
                continue
                
            txt = page.extract_text() or ""
            if txt.strip():
                texts.append(txt)
    
    if page_numbers is not None:
        logging.info("Extracted text from %d specified pages", len(page_numbers))
    
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
    Build FAISS indices for text chunks and image pages, saving metadata. 
    Only processes text from pages without images/charts/tables, and only 
    converts pages with visual content to images.
    """
    text_vectors, image_vectors = [], []
    text_meta, image_meta = [], []

    for pdf_path in pdf_paths:
        uid = str(uuid.uuid4())
        filename = os.path.basename(pdf_path)
        
        # Analyze pages to determine which have visual content
        text_only_pages, visual_pages = analyze_pdf_pages(pdf_path)
        
        logging.info(f"Processing {filename}: {len(text_only_pages)} text pages, " +
                    f"{len(visual_pages)} visual pages")

        # --- Text chunks (only from text-only pages) ---
        if text_only_pages:
            raw_text = extract_text_from_pdf(pdf_path, text_only_pages)
            for i, chunk in enumerate(chunk_text(raw_text)):
                vec = embed_text(chunk)
                text_vectors.append(vec)
                text_meta.append({
                    "doc_id": f"{uid}_txt_{i}",
                    "source": filename,
                    "chunk": i,
                    "content": chunk,
                    "pages": sorted(list(text_only_pages)),  # Track which pages
                })

        # --- Image pages (only visual content pages) ---
        if visual_pages:
            for page_num, img in pdf_to_images(pdf_path, visual_pages):
                vec = embed_image(img)
                image_vectors.append(vec)
                # Save a preview image to disk
                preview_fname = f"{uid}_img_{page_num}.png"
                preview_path = os.path.join(data_dir, preview_fname)
                img.save(preview_path)

                image_meta.append({
                    "doc_id": f"{uid}_img_{page_num}",
                    "source": filename,
                    "page": page_num + 1,  # Convert to 1-indexed for user display
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
