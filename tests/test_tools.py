"""
Tests for individual tools (unit tests, no LLM or Docker required for most)
"""
import sys
import os
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
import pytest_asyncio


# ─────────────────────────────────────────────────────────────────────────────
#  OCR Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOCRTool:
    """Tests for backend/tools/ocr.py"""

    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_failure(self):
        from tools.ocr import run_ocr
        result = await run_ocr("/nonexistent/path/file.pdf")
        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["text"] == ""
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_image_ocr_success(self):
        """Create a simple test image and OCR it."""
        try:
            from PIL import Image, ImageDraw
            import pytesseract
        except ImportError:
            pytest.skip("PIL/pytesseract not installed")

        # Check if Tesseract is actually installed and accessible
        import subprocess
        try:
            from config import TESSERACT_CMD
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            version = pytesseract.get_tesseract_version()
        except Exception:
            pytest.skip(
                "Tesseract OCR not installed or not found. "
                "Install from https://github.com/UB-Mannheim/tesseract/wiki "
                "and update TESSERACT_CMD in config.py"
            )

        from tools.ocr import run_ocr

        # Create a white image with text
        img = Image.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Hello SovereignForge", fill="black")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            tmp_path = tmp.name

        try:
            result = await run_ocr(tmp_path)
            # OCR should succeed (text extraction may vary by installation)
            assert result["success"] is True
            assert result["pages"] == 1
            assert result["error"] is None
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_unsupported_extension_treated_as_image(self):
        """Non-PDF files go through image path."""
        from tools.ocr import run_ocr
        # This will fail since file doesn't exist, but should not crash
        result = await run_ocr("/tmp/test.bmp")
        # Either success=False (file not found) or a real result
        assert "success" in result


# ─────────────────────────────────────────────────────────────────────────────
#  Extract Tool Tests  (only test the parsing, not the LLM call)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractParsing:
    """Test the JSON parsing logic in extract.py."""

    def test_parse_clean_json(self):
        from tools.extract import _parse_response
        response = '{"summary": "Test", "findings": ["f1"], "risks": [], "recommendations": ["r1"]}'
        result = _parse_response(response)
        assert result["success"] is True
        assert result["summary"] == "Test"
        assert result["findings"] == ["f1"]

    def test_parse_json_with_markdown_fences(self):
        from tools.extract import _parse_response
        response = '```json\n{"summary": "Test", "findings": ["f1"], "risks": [], "recommendations": []}\n```'
        result = _parse_response(response)
        assert result["success"] is True

    def test_parse_json_embedded_in_text(self):
        from tools.extract import _parse_response
        response = 'Here is the result: {"summary": "Summary", "findings": ["f"], "risks": ["r"], "recommendations": []}'
        result = _parse_response(response)
        assert result["success"] is True

    def test_parse_invalid_json_returns_failure(self):
        from tools.extract import _parse_response
        response = "This is not JSON at all"
        result = _parse_response(response)
        assert result["success"] is False
        assert result["findings"] == ["This is not JSON at all"]

    def test_ensure_list_handles_string(self):
        from tools.extract import _ensure_list
        assert _ensure_list("single") == ["single"]
        assert _ensure_list(["a", "b"]) == ["a", "b"]
        assert _ensure_list(None) == []


# ─────────────────────────────────────────────────────────────────────────────
#  Draft Word Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftWordTool:

    @pytest.mark.asyncio
    async def test_generates_docx_file(self):
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        from tools.draft_word import run_draft_word

        data = {
            "summary": "This is a test summary.",
            "findings": ["Finding 1", "Finding 2"],
            "risks": ["Risk 1"],
            "recommendations": ["Recommendation 1"],
        }

        result = await run_draft_word(data, "test_doc", "Test Document")

        assert result["success"] is True
        assert result["file_path"].endswith(".docx")
        assert os.path.exists(result["file_path"])
        assert result["error"] is None

        # Verify it's a valid docx
        doc = Document(result["file_path"])
        full_text = "\n".join([p.text for p in doc.paragraphs])
        assert "Test Document" in full_text or "test_doc" in result["filename"]

        # Cleanup
        os.unlink(result["file_path"])

    @pytest.mark.asyncio
    async def test_handles_empty_data_gracefully(self):
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        from tools.draft_word import run_draft_word

        result = await run_draft_word({})
        assert result["success"] is True
        assert os.path.exists(result["file_path"])
        os.unlink(result["file_path"])


# ─────────────────────────────────────────────────────────────────────────────
#  Task Router Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskRouterIntegration:

    def test_full_classification_pipeline(self):
        from router.task_router import classify_task

        test_cases = [
            ("analyze this PDF report", "/tmp/report.pdf", "document"),
            ("write python code to sort a list", None, "coding"),
            ("what is in this image", "/tmp/photo.jpg", "multimodal"),
        ]

        for user_input, file_path, expected_type in test_cases:
            result = classify_task(user_input, file_path)
            assert result["task_type"] == expected_type, (
                f"Expected {expected_type} for '{user_input}' but got {result['task_type']}"
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Agent Loop Tests (parsing only, no LLM)
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentLoopParsing:

    def test_parse_clean_json_response(self):
        from agent.loop import _parse_llm_response
        raw = '{"thought": "test", "action": "ocr", "action_input": {"file_path": "/tmp/test.pdf"}, "observation": null}'
        result = _parse_llm_response(raw)
        assert result is not None
        assert result["action"] == "ocr"
        assert result["thought"] == "test"

    def test_parse_json_with_fences(self):
        from agent.loop import _parse_llm_response
        raw = '```json\n{"thought": "thinking", "action": "finish", "action_input": {"answer": "done"}, "observation": null}\n```'
        result = _parse_llm_response(raw)
        assert result is not None
        assert result["action"] == "finish"

    def test_parse_returns_none_for_garbage(self):
        from agent.loop import _parse_llm_response
        result = _parse_llm_response("This is just plain text with no JSON")
        assert result is None

    def test_parse_empty_string(self):
        from agent.loop import _parse_llm_response
        result = _parse_llm_response("")
        assert result is None

    def test_truncate_result(self):
        from agent.loop import _truncate_result
        result = {"text": "a" * 1000, "pages": 5}
        truncated = _truncate_result(result, max_chars=100)
        assert len(truncated["text"]) <= 150  # 100 + truncation message
        assert truncated["pages"] == 5
