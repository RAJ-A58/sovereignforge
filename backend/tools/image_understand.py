"""Image Understand Tool — analyze images and PDFs using a local vision LLM."""
import sys
import asyncio
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import registry

DEFAULT_QUESTION = (
    "Describe everything in this image in detail. "
    "Extract all visible text. "
    "Identify all objects, diagrams, tables, charts, and key visual elements. "
    "If this is a document, summarize its content and structure."
)


async def run_image_understand(
    file_path: str,
    question: str = DEFAULT_QUESTION,
) -> dict:
    """
    Analyze an image or PDF page using the local vision model.

    Args:
        file_path: Absolute path to image or PDF file
        question:  Question to ask the vision model about the image

    Returns:
        {
            "success": bool,
            "analysis": str,
            "extracted_text": str,
            "objects_found": list[str],
            "error": str|None
        }
    """
    path = Path(file_path)

    if not path.exists():
        return _failure(f"File not found: {file_path}")

    try:
        # Convert PDF first page to image if needed
        if path.suffix.lower() == ".pdf":
            image_path = await _pdf_first_page_to_image(path)
            cleanup = True
        else:
            image_path = str(path)
            cleanup = False

        # Send to vision model
        analysis = await registry.generate_vision(question, image_path)

        # Clean up temp file if we created one
        if cleanup and os.path.exists(image_path):
            os.remove(image_path)

        return {
            "success": True,
            "analysis": analysis,
            "extracted_text": analysis,   # VLM extracts text inline
            "objects_found": [],           # Can be parsed from analysis if needed
            "error": None,
        }

    except Exception as exc:
        return _failure(str(exc))


async def _pdf_first_page_to_image(path: Path) -> str:
    """Convert the first page of a PDF to a JPEG temp file."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise RuntimeError("pdf2image not installed. Run: pip install pdf2image")

    loop = asyncio.get_event_loop()

    def _convert():
        images = convert_from_path(str(path), dpi=150, first_page=1, last_page=1)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        images[0].save(tmp.name, "JPEG")
        return tmp.name

    return await loop.run_in_executor(None, _convert)


def _failure(error: str) -> dict:
    return {
        "success": False,
        "analysis": "",
        "extracted_text": "",
        "objects_found": [],
        "error": error,
    }
