"""
Tests for the Task Router
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from router.task_router import classify_task


class TestFileExtensionClassification:
    """File extension should be the strongest signal."""

    def test_pdf_is_document(self):
        result = classify_task("analyze this", "/path/to/report.pdf")
        assert result["task_type"] == "document"
        assert result["model_key"] == "reasoning"
        assert result["confidence"] >= 0.90

    def test_png_is_multimodal(self):
        result = classify_task("what is this", "/path/to/image.png")
        assert result["task_type"] == "multimodal"
        assert result["model_key"] == "vision"

    def test_jpg_is_multimodal(self):
        result = classify_task("describe this", "/path/to/photo.jpg")
        assert result["task_type"] == "multimodal"
        assert result["model_key"] == "vision"

    def test_py_file_is_coding(self):
        result = classify_task("debug this", "/path/to/script.py")
        assert result["task_type"] == "coding"
        assert result["model_key"] == "coding"

    def test_docx_is_document(self):
        result = classify_task("read this", "/path/to/contract.docx")
        assert result["task_type"] == "document"

    def test_ts_file_is_coding(self):
        result = classify_task("review this", "/path/to/app.ts")
        assert result["task_type"] == "coding"


class TestKeywordClassification:
    """Keyword scoring for text-only inputs."""

    def test_coding_keywords(self):
        result = classify_task("write a python function to sort a list")
        assert result["task_type"] == "coding"
        assert result["model_key"] == "coding"

    def test_document_keywords(self):
        result = classify_task("summarize this report and extract the key findings")
        assert result["task_type"] == "document"

    def test_multimodal_keywords(self):
        result = classify_task("describe this image and identify all objects")
        assert result["task_type"] == "multimodal"

    def test_debug_keyword(self):
        result = classify_task("debug this code and fix the error")
        assert result["task_type"] == "coding"

    def test_ambiguous_defaults_to_document(self):
        result = classify_task("help me")
        assert result["task_type"] == "document"
        assert result["confidence"] <= 0.50

    def test_image_with_code_question_is_coding(self):
        result = classify_task(
            "write python script to parse this data",
            "/path/to/chart.png"
        )
        # Image file + coding keywords → coding
        assert result["task_type"] == "coding"


class TestResultFormat:
    """Always returns required keys."""

    def test_result_has_required_keys(self):
        result = classify_task("test input")
        assert "task_type" in result
        assert "confidence" in result
        assert "model_key" in result
        assert "reasoning" in result

    def test_confidence_is_in_range(self):
        result = classify_task("write a python algorithm")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_task_type_is_valid(self):
        result = classify_task("some input text here")
        assert result["task_type"] in ("document", "coding", "multimodal")

    def test_model_key_is_valid(self):
        result = classify_task("some input text here")
        assert result["model_key"] in ("reasoning", "coding", "vision")
