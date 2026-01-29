"""
PDF Text Extraction Service for CareerAssist

Uses pdfplumber for reliable CV/resume text extraction with:
- Layout preservation (handles multi-column CVs)
- Table handling
- Multi-page support

Design Log: /design-log/frontend/011-cv-pdf-upload-parser.md
"""

import logging
from io import BytesIO
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when PDF text extraction fails"""
    pass


def extract_text_from_pdf(
    file_bytes: bytes,
    preserve_layout: bool = True,
    max_pages: int = 20
) -> str:
    """
    Extract text from a PDF file.
    
    Uses pdfplumber with layout=True to preserve visual layout,
    which is critical for multi-column CVs where simple extraction
    would interleave text from different columns incorrectly.
    
    Args:
        file_bytes: Raw PDF file bytes
        preserve_layout: If True, preserves visual layout (recommended for CVs)
        max_pages: Maximum pages to process (CVs are typically 1-3 pages)
        
    Returns:
        Extracted text content
        
    Raises:
        PDFExtractionError: If extraction fails or PDF is invalid
    """
    try:
        text_parts = []
        
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if len(pdf.pages) == 0:
                raise PDFExtractionError("PDF has no pages")
            
            if len(pdf.pages) > max_pages:
                raise PDFExtractionError(
                    f"PDF has too many pages ({len(pdf.pages)}). "
                    f"Maximum is {max_pages} pages. CVs are typically 1-3 pages."
                )
            
            for page_num, page in enumerate(pdf.pages, 1):
                logger.debug(f"Extracting page {page_num}/{len(pdf.pages)}")
                
                if preserve_layout:
                    # Layout mode preserves visual structure
                    # Critical for multi-column CVs
                    text = page.extract_text(
                        layout=True,
                        x_tolerance=3,  # Character spacing tolerance
                        y_tolerance=3   # Line spacing tolerance
                    )
                else:
                    text = page.extract_text()
                
                if text:
                    text_parts.append(text.strip())
        
        full_text = "\n\n".join(text_parts)
        
        # Check if we got meaningful content
        if len(full_text.strip()) < 50:
            raise PDFExtractionError(
                "Could not extract enough text from PDF. "
                "The PDF may be scanned/image-based. "
                "Please use a PDF with selectable text."
            )
        
        logger.info(
            f"Extracted {len(full_text)} characters from "
            f"{len(text_parts)} page(s)"
        )
        return full_text
        
    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
        raise PDFExtractionError(f"Invalid PDF format: {e}")
    except pdfplumber.pdfminer.pdfdocument.PDFPasswordIncorrect:
        raise PDFExtractionError(
            "PDF is password protected. "
            "Please remove the password and try again."
        )
    except Exception as e:
        if isinstance(e, PDFExtractionError):
            raise
        logger.error(f"PDF extraction failed: {e}", exc_info=True)
        raise PDFExtractionError(f"Failed to extract text from PDF: {e}")


def validate_pdf_file(
    file_bytes: bytes,
    max_size_mb: float = 5.0
) -> Optional[str]:
    """
    Validate a PDF file before processing.
    
    Args:
        file_bytes: Raw PDF file bytes
        max_size_mb: Maximum file size in MB
        
    Returns:
        Error message if invalid, None if valid
    """
    # Check size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return f"File too large ({size_mb:.1f}MB). Maximum size is {max_size_mb}MB."
    
    # Check PDF magic bytes
    if not file_bytes.startswith(b'%PDF'):
        return "File is not a valid PDF"
    
    # Check for empty file
    if len(file_bytes) < 100:
        return "File is too small to be a valid PDF"
    
    return None
