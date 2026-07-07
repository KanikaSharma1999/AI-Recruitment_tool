"""
services/pdf_extractor.py
==========================
Stage 1 of the Hybrid Parsing Pipeline — PDF Extraction.

Replaces PyPDF2 with PyMuPDF (fitz) for:
  • Preserved reading order
  • Multi-page support
  • Multi-column layout handling
  • Heading / section ordering preservation
  • Better handling of modern resume templates

Falls back to PyPDF2 if PyMuPDF is not installed.
Falls back to mammoth for .docx files.
"""

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── PyMuPDF (fitz) ────────────────────────────────────────────────────────────
_HAS_FITZ = False
try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
    logger.info("[PDFExtractor] PyMuPDF (fitz) loaded successfully.")
except ImportError:
    logger.warning("[PDFExtractor] PyMuPDF not installed. Falling back to PyPDF2.")

# ── PyPDF2 fallback ───────────────────────────────────────────────────────────
_HAS_PYPDF2 = False
try:
    from PyPDF2 import PdfReader as _PdfReader
    _HAS_PYPDF2 = True
except ImportError:
    pass

# ── mammoth (DOCX) ───────────────────────────────────────────────────────────
_HAS_MAMMOTH = False
try:
    import mammoth as _mammoth
    _HAS_MAMMOTH = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  PyMuPDF extraction (primary)
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_with_fitz(content: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF.

    Strategy:
      1. For each page, use get_text("blocks") to get sorted text blocks.
      2. Sort blocks by vertical position (y0) then horizontal (x0) to handle
         multi-column layouts with natural reading order.
      3. Preserve paragraph separation with double newlines.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        pages_text = []

        for page_num, page in enumerate(doc):
            # "blocks" returns (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks")

            # Sort by top-to-bottom then left-to-right
            # Group columns: blocks with x0 < page_width/2 are "left column"
            page_width = page.rect.width
            left_blocks  = [b for b in blocks if b[0] < page_width * 0.55 and b[6] == 0]
            right_blocks = [b for b in blocks if b[0] >= page_width * 0.45 and b[6] == 0]

            # Check if document is truly multi-column
            is_multicolumn = (
                left_blocks and right_blocks
                and abs(len(left_blocks) - len(right_blocks)) < max(len(left_blocks), len(right_blocks))
                and max((b[0] for b in right_blocks), default=0) > page_width * 0.45
            )

            if is_multicolumn:
                # Read left column first, then right column (natural reading order)
                sorted_left  = sorted(left_blocks,  key=lambda b: (b[1], b[0]))
                sorted_right = sorted(right_blocks, key=lambda b: (b[1], b[0]))
                ordered = sorted_left + sorted_right
            else:
                # Single-column: sort all text blocks top-to-bottom
                all_text_blocks = [b for b in blocks if b[6] == 0]
                ordered = sorted(all_text_blocks, key=lambda b: (round(b[1] / 10) * 10, b[0]))

            page_text = "\n".join(b[4].strip() for b in ordered if b[4].strip())
            if page_text:
                pages_text.append(page_text)

        doc.close()
        return "\n\n".join(pages_text)

    except Exception as exc:
        logger.error("[PDFExtractor] PyMuPDF extraction failed: %s", exc)
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  PyPDF2 fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_with_pypdf2(content: bytes) -> str:
    """Legacy PyPDF2 extraction — used only when PyMuPDF is unavailable."""
    if not _HAS_PYPDF2:
        return ""
    try:
        reader = _PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception as exc:
        logger.error("[PDFExtractor] PyPDF2 extraction failed: %s", exc)
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  DOCX extraction
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_docx(content: bytes) -> str:
    """Extract plain text from .docx bytes using mammoth."""
    if not _HAS_MAMMOTH:
        logger.warning("[PDFExtractor] mammoth not installed — cannot extract DOCX.")
        return ""
    try:
        result = _mammoth.extract_raw_text(io.BytesIO(content))
        return result.value or ""
    except Exception as exc:
        logger.error("[PDFExtractor] mammoth DOCX extraction failed: %s", exc)
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  TXT extraction
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_txt(content: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """
    Primary entry point.

    Detects file type from filename extension and routes to the appropriate
    extraction strategy.  Always returns a str (possibly empty on failure).

    PDF  → PyMuPDF  → PyPDF2 fallback
    DOCX → mammoth
    TXT  → UTF-8/latin-1 decode
    """
    if not content:
        return ""

    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text = _extract_with_fitz(content) if _HAS_FITZ else ""
        if not text.strip() and _HAS_PYPDF2:
            logger.info("[PDFExtractor] PyMuPDF returned empty — trying PyPDF2 fallback.")
            text = _extract_with_pypdf2(content)
        if not text.strip():
            logger.warning("[PDFExtractor] PDF extraction produced no text for '%s'.", filename)
        return text

    elif ext in (".docx", ".doc"):
        return _extract_docx(content)

    elif ext == ".txt":
        return _extract_txt(content)

    else:
        # Try PDF extraction as last resort
        if _HAS_FITZ:
            return _extract_with_fitz(content)
        return ""


# ── Convenience wrappers (backward-compat) ────────────────────────────────────

def read_pdf_bytes(content: bytes) -> str:
    """Backward-compatible wrapper used by resume_parser.py."""
    return extract_text_from_bytes(content, "resume.pdf")


def read_docx_bytes(content: bytes) -> str:
    """Backward-compatible wrapper."""
    return extract_text_from_bytes(content, "resume.docx")
