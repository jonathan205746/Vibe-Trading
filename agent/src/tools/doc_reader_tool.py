"""Document reader tool: full PDF text extraction with OCR fallback for image/scanned pages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from src.agent.tools import BaseTool

_MAX_CHARS = 15000  # truncation threshold
_MIN_TEXT_PER_PAGE = 50  # pages with fewer chars are treated as image pages and fall back to OCR
_ocr_engine = None


def _get_ocr():
    """Lazily load the RapidOCR engine (first call takes ~1-2s)."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _ocr_page(doc, page_idx: int) -> str:
    """Render a PDF page to an image and run OCR on it.

    Args:
        doc: pypdfium2 PdfDocument object.
        page_idx: Zero-based page index.

    Returns:
        OCR-extracted text for the page.
    """
    import numpy as np

    page = doc[page_idx]
    bitmap = page.render(scale=300 / 72)
    img = bitmap.to_numpy()

    ocr = _get_ocr()
    result, _ = ocr(img)
    if not result:
        return ""
    # result is list of [bbox, text, confidence]
    lines = [item[1] for item in result]
    return "\n".join(lines)


def read_document(file_path: str, pages: str = "") -> str:
    """Extract text from a PDF document, falling back to OCR for image pages.

    Args:
        file_path: Absolute path to the PDF file.
        pages: Page range (e.g. "1-10", "5", "1,3,5-8"); empty means all pages.

    Returns:
        JSON-formatted result.
    """
    path = Path(file_path)
    if not path.exists():
        return json.dumps({"status": "error", "error": f"File not found: {file_path}"}, ensure_ascii=False)
    if path.suffix.lower() != ".pdf":
        return json.dumps({"status": "error", "error": f"Only PDF supported, got: {path.suffix}"}, ensure_ascii=False)

    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path))
        total_pages = len(doc)
        target_pages = _parse_pages(pages, total_pages) if pages.strip() else list(range(total_pages))

        texts = []
        ocr_pages = 0
        for i in target_pages:
            if 0 <= i < total_pages:
                page = doc[i]
                text = page.get_textpage().get_text_range().strip()

                if len(text) >= _MIN_TEXT_PER_PAGE:
                    texts.append(f"--- Page {i + 1} ---\n{text}")
                else:
                    # Too little text — fall back to OCR
                    ocr_text = _ocr_page(doc, i)
                    if ocr_text.strip():
                        texts.append(f"--- Page {i + 1} [OCR] ---\n{ocr_text}")
                        ocr_pages += 1
                    elif text:
                        # OCR also found nothing; use whatever text exists
                        texts.append(f"--- Page {i + 1} ---\n{text}")

        doc.close()
        full_text = "\n\n".join(texts)
        char_count = len(full_text)

        truncated = False
        if char_count > _MAX_CHARS:
            full_text = full_text[:_MAX_CHARS] + f"\n\n... (truncated, total {char_count} chars, {total_pages} pages)"
            truncated = True

        return json.dumps({
            "status": "ok",
            "file": path.name,
            "total_pages": total_pages,
            "pages_read": len(target_pages),
            "ocr_pages": ocr_pages,
            "char_count": char_count,
            "truncated": truncated,
            "text": full_text,
        }, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)


def _parse_pages(pages_str: str, total: int) -> list:
    """Parse a page-range string into a list of zero-based page indices.

    Args:
        pages_str: e.g. "1-10", "5", "1,3,5-8".
        total: Total number of pages in the document.

    Returns:
        Sorted list of zero-based page indices.
    """
    result = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            s = max(int(start.strip()) - 1, 0)
            e = min(int(end.strip()), total)
            result.extend(range(s, e))
        elif part.isdigit():
            result.append(int(part) - 1)
    return sorted(set(result))


class DocReaderTool(BaseTool):
    """PDF document reader tool."""

    name = "read_document"
    description = "Read a PDF document: extract text pages + OCR for image/scanned pages. Supports research papers, financial reports, etc. Accepts optional page ranges."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the PDF file"},
            "pages": {"type": "string", "description": "Page range (e.g. '1-10', '5', '1,3,5-8'); leave empty for all pages", "default": ""},
        },
        "required": ["file_path"],
    }
    repeatable = True

    def execute(self, **kwargs) -> str:
        """Read PDF document."""
        return read_document(kwargs["file_path"], kwargs.get("pages", ""))
