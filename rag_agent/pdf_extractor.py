"""
Simple PDF Text Extractor

A straightforward PDF text extraction utility without complex dependencies.
Uses pypdf for basic PDF text extraction.
"""

import logging
from pathlib import Path
from typing import List, Optional
import pypdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplePDFExtractor:
    """Simple PDF text extractor using pypdf."""

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text as a single string
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text_parts = []

                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")

                full_text = "\n\n".join(text_parts)
                logger.info(f"Extracted {len(full_text)} characters from {Path(pdf_path).name}")
                return full_text

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return ""

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks by word count.

        Args:
            text: Text to chunk
            chunk_size: Number of words per chunk
            overlap: Number of overlapping words between chunks

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        if len(words) <= chunk_size:
            return [text]

        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            if end >= len(words):
                break

            start += (chunk_size - overlap)

        logger.info(f"Created {len(chunks)} chunks from {len(words)} words")
        return chunks


# Convenience function
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text
    """
    extractor = SimplePDFExtractor()
    return extractor.extract_text(pdf_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        extractor = SimplePDFExtractor()
        text = extractor.extract_text(pdf_path)
        print(f"\nExtracted {len(text)} characters")
        print("\nFirst 500 characters:")
        print(text[:500])
    else:
        print("Usage: python pdf_extractor.py <pdf_path>")
