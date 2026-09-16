"""OCR Tool — extract text from PDF or image files using Tesseract."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytesseract
from PIL import Image
from config import TESSERACT_CMD, OCR_DPI

# Configure Tesseract path (Windows needs explicit path)
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


async def run_ocr(file_path: str) -> dict:
    """
    Extract text from a PDF or image file using Tesseract OCR.

    Args:
        file_path: Absolute path to the file (.pdf, .jpg, .png, etc.)

    Returns:
        {
            "success": bool,
            "text": str,       -- full extracted text
            "pages": int,      -- number of pages processed
            "error": str|None
        }
    """
    path = Path(file_path)

    if not path.exists():
        return {"success": False, "text": "", "pages": 0,
                "error": f"File not found: {file_path}"}

    try:
        if path.suffix.lower() == ".pdf":
            return await _ocr_pdf(path)
        else:
            return await _ocr_image(path)
    except Exception as exc:
        return {"success": False, "text": "", "pages": 0, "error": str(exc)}


async def _ocr_pdf(path: Path) -> dict:
    """Convert PDF pages to images then run OCR on each page."""
    # Import here so OCR tool works without pdf2image if not needed
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return {"success": False, "text": "", "pages": 0,
                "error": "pdf2image not installed. Run: pip install pdf2image"}

    # Run in thread executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()

    def _do_pdf_ocr():
        images = convert_from_path(str(path), dpi=OCR_DPI)
        all_text = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang="eng")
            all_text.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(all_text), len(images)

    full_text, pages = await loop.run_in_executor(None, _do_pdf_ocr)

    return {
        "success": True,
        "text": full_text.strip(),
        "pages": pages,
        "error": None,
    }


async def _ocr_image(path: Path) -> dict:
    """Run OCR directly on an image file."""
    loop = asyncio.get_event_loop()

    def _do_image_ocr():
        img = Image.open(str(path))
        return pytesseract.image_to_string(img, lang="eng")

    text = await loop.run_in_executor(None, _do_image_ocr)

    return {
        "success": True,
        "text": text.strip(),
        "pages": 1,
        "error": None,
    }
