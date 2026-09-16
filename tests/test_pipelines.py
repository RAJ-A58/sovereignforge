"""
End-to-end pipeline tests.

Pipeline A: Document    → OCR → Extract → Draft Word
Pipeline B: Coding      → Code Sandbox
Pipeline C: Multimodal  → Image Understand (VLM)

These tests do:
  - Real tool calls (OCR, extract, draft_word) with mocked LLM for extract/VLM
  - Verify the full data flow through each pipeline
  - Check output files are generated correctly
"""
import sys
import os
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_text():
    """Sample document text for testing extract + draft_word."""
    return """
    INSPECTION REPORT — Electrical Systems
    Date: September 2026

    SUMMARY:
    This report covers the quarterly inspection of the building's electrical systems.
    Several issues were identified that require immediate attention.

    FINDINGS:
    1. Main circuit breaker panel shows signs of overheating.
    2. Wiring in sections B and C is non-compliant with current standards.
    3. Emergency lighting system tested successfully on all floors.
    4. Grounding system requires upgrading in the basement.

    RISKS:
    - Risk of electrical fire due to overheating panel (HIGH).
    - Non-compliance with IEC 60364 standards (MEDIUM).

    RECOMMENDATIONS:
    - Replace main circuit breaker panel immediately.
    - Schedule wiring upgrade for sections B and C within 30 days.
    - Document emergency lighting test results.
    """


@pytest.fixture
def sample_python_code():
    """Sample Python code for sandbox testing."""
    return """
def find_duplicates(data):
    seen = set()
    duplicates = []
    for item in data:
        if item in seen:
            duplicates.append(item)
        else:
            seen.add(item)
    return duplicates

# Test
test_data = [1, 2, 3, 2, 4, 5, 3, 6]
result = find_duplicates(test_data)
print("Duplicates:", result)
print("Count:", len(result))
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline A: Document Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentPipeline:

    @pytest.mark.asyncio
    async def test_extract_parses_sample_text(self, sample_text):
        """Test extract tool with mocked LLM response."""
        from tools.extract import _parse_response

        # Simulate what LLM would return
        mock_llm_output = '''{"summary": "Electrical inspection report with critical findings.", "findings": ["Main circuit breaker overheating", "Non-compliant wiring in sections B and C"], "risks": ["Risk of electrical fire (HIGH)", "Non-compliance with IEC 60364 (MEDIUM)"], "recommendations": ["Replace main circuit breaker immediately", "Schedule wiring upgrade within 30 days"]}'''

        result = _parse_response(mock_llm_output)
        assert result["success"] is True
        assert len(result["findings"]) >= 2
        assert len(result["risks"]) >= 1
        assert len(result["recommendations"]) >= 1
        assert len(result["summary"]) > 10

    @pytest.mark.asyncio
    async def test_draft_word_from_extracted_data(self):
        """Test Word document generation from extracted data."""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        from tools.draft_word import run_draft_word

        extracted_data = {
            "summary": "Electrical inspection with critical findings requiring immediate action.",
            "findings": [
                "Main circuit breaker panel shows signs of overheating",
                "Wiring in sections B and C is non-compliant",
            ],
            "risks": [
                "Risk of electrical fire due to overheating (HIGH)",
            ],
            "recommendations": [
                "Replace main circuit breaker panel immediately",
                "Schedule wiring upgrade within 30 days",
            ],
        }

        result = await run_draft_word(
            extracted_data,
            document_type="inspection_note",
            title="Electrical Inspection — Approval Note",
        )

        assert result["success"] is True, f"Draft failed: {result.get('error')}"
        assert result["file_path"].endswith(".docx")
        assert os.path.exists(result["file_path"])

        # Verify docx content
        doc = Document(result["file_path"])
        all_text = " ".join(p.text for p in doc.paragraphs)
        assert "Electrical Inspection" in all_text
        assert "overheating" in all_text.lower() or "circuit" in all_text.lower()

        print(f"\n✅ Pipeline A: Document generated → {result['filename']}")
        os.unlink(result["file_path"])

    @pytest.mark.asyncio
    async def test_extract_with_mocked_llm(self, sample_text):
        """Full extract tool call with mocked LLM."""
        mock_response = '{"summary": "Test summary.", "findings": ["Finding 1"], "risks": ["Risk 1"], "recommendations": ["Rec 1"]}'

        with patch("tools.extract.registry") as mock_registry:
            mock_registry.generate = AsyncMock(return_value=mock_response)

            from tools.extract import run_extract
            result = await run_extract(sample_text, "findings and risks")

        assert result["success"] is True
        assert result["summary"] == "Test summary."
        assert "Finding 1" in result["findings"]

        print("\n✅ Pipeline A: Extract → mocked LLM works")


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline B: Coding Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestCodingPipeline:

    @pytest.mark.asyncio
    async def test_sandbox_executes_simple_code(self, sample_python_code):
        """Test code sandbox with a simple Python script."""
        try:
            import docker
            client = docker.from_env()
            client.ping()  # Will fail if Docker Desktop is not running
        except Exception as e:
            pytest.skip(f"Docker not available or not running: {e}")

        from tools.code_sandbox import run_code_sandbox

        result = await run_code_sandbox(sample_python_code)

        if not result["success"] and "not found" in result["stderr"].lower():
            pytest.skip("Sandbox Docker image not built — run: docker build -t sovereignforge-sandbox:latest ./sandbox/")

        assert result["success"] is True, f"Sandbox failed: {result['stderr']}"
        assert "Duplicates:" in result["stdout"]
        assert "[2, 3]" in result["stdout"] or "2, 3" in result["stdout"]
        assert result["timed_out"] is False

        print(f"\n✅ Pipeline B: Code sandbox output → {result['stdout'].strip()}")

    @pytest.mark.asyncio
    async def test_sandbox_handles_syntax_error(self):
        """Code with syntax error should fail gracefully."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
        except Exception as e:
            pytest.skip(f"Docker not available or not running: {e}")

        from tools.code_sandbox import run_code_sandbox

        bad_code = "def broken(\n    print('oops')\n"  # syntax error
        result = await run_code_sandbox(bad_code)

        if "not found" in result.get("stderr", "").lower() and "image" in result.get("stderr", "").lower():
            pytest.skip("Sandbox Docker image not built")

        # Should fail but not crash (not timeout)
        assert result["timed_out"] is False
        assert "stderr" in result

        print("\n✅ Pipeline B: Syntax error handled gracefully")

    @pytest.mark.asyncio
    async def test_sandbox_fibonacci(self):
        """Classic test: Fibonacci sequence."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
        except Exception as e:
            pytest.skip(f"Docker not available or not running: {e}")

        from tools.code_sandbox import run_code_sandbox

        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = [fibonacci(i) for i in range(10)]
print(result)
"""
        result = await run_code_sandbox(code)

        if "not found" in result.get("stderr", "").lower() and "image" in result.get("stderr", "").lower():
            pytest.skip("Sandbox Docker image not built")

        assert result["success"] is True
        assert "0" in result["stdout"]
        assert "1" in result["stdout"]

        print(f"\n✅ Pipeline B: Fibonacci → {result['stdout'].strip()}")


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline C: Multimodal Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestMultimodalPipeline:

    @pytest.mark.asyncio
    async def test_image_understand_with_mocked_vlm(self):
        """Test image_understand with mocked vision model."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        # Create a temp test image
        img = Image.new("RGB", (200, 100), color=(0, 100, 200))
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img.save(tmp.name, "JPEG")
            tmp_path = tmp.name

        mock_analysis = "This is a blue rectangle image. No text visible. The image is a solid blue color (RGB: 0, 100, 200)."

        try:
            with patch("tools.image_understand.registry") as mock_registry:
                mock_registry.generate_vision = AsyncMock(return_value=mock_analysis)

                from tools.image_understand import run_image_understand
                result = await run_image_understand(tmp_path, "What is in this image?")

            assert result["success"] is True
            assert result["analysis"] == mock_analysis
            assert len(result["extracted_text"]) > 0
            assert result["error"] is None

            print(f"\n✅ Pipeline C: Image analysis → {result['analysis'][:80]}...")
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_image_understand_nonexistent_file(self):
        """Should fail gracefully for missing files."""
        from tools.image_understand import run_image_understand

        result = await run_image_understand("/nonexistent/image.jpg")
        assert result["success"] is False
        assert "not found" in result["error"].lower()


# ─────────────────────────────────────────────────────────────────────────────
#  Full End-to-End Agent Pipeline Tests (with mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

class TestFullAgentPipelines:

    @pytest.mark.asyncio
    async def test_document_agent_pipeline(self, sample_text):
        """
        Simulate the agent going through: extract → draft_word → finish
        with mocked LLM calls.
        """
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        from agent.loop import run_agent

        # Step 1: agent calls extract
        extract_call = '{"thought": "I need to extract data from this text", "action": "extract", "action_input": {"raw_text": "Sample text", "extraction_goal": "findings and risks"}, "observation": null}'
        # Step 2: agent calls draft_word
        draft_call = '{"thought": "Now I will draft the Word document", "action": "draft_word", "action_input": {"extracted_data": {"summary": "Electrical report.", "findings": ["Finding 1"], "risks": ["Risk 1"], "recommendations": ["Rec 1"]}, "document_type": "approval_note", "title": "Test Report"}, "observation": null}'
        # Step 3: finish
        finish_call = '{"thought": "Task complete", "action": "finish", "action_input": {"answer": "I have extracted findings and drafted the Word document.", "artifacts": []}, "observation": null}'

        responses = [extract_call, draft_call, finish_call]
        call_index = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_index
            response = responses[min(call_index, len(responses) - 1)]
            call_index += 1
            return response

        mock_extract_result = {
            "success": True,
            "summary": "Electrical report.",
            "findings": ["Finding 1"],
            "risks": ["Risk 1"],
            "recommendations": ["Rec 1"],
            "raw_json": {},
        }

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = mock_generate
            with patch("agent.loop.run_extract", AsyncMock(return_value=mock_extract_result)):
                events = []
                async for event in run_agent(
                    user_input="Extract findings from this document",
                    task_type="document",
                    model_key="reasoning",
                ):
                    events.append(event)

        event_types = [e.type for e in events]
        assert "finish" in event_types or "tool_call" in event_types

        finish_events = [e for e in events if e.type == "finish"]
        if finish_events:
            print(f"\n✅ Full Document Pipeline: {finish_events[0].data['answer'][:80]}")

    @pytest.mark.asyncio
    async def test_coding_agent_pipeline(self, sample_python_code):
        """
        Simulate: code_sandbox → finish with mocked LLM.
        """
        from agent.loop import run_agent

        sandbox_call = f'{{"thought": "I will execute this code", "action": "code_sandbox", "action_input": {{"code": "print(42)", "language": "python"}}, "observation": null}}'
        finish_call = '{"thought": "Code executed successfully", "action": "finish", "action_input": {"answer": "The code runs and outputs 42.", "artifacts": []}, "observation": null}'

        responses = [sandbox_call, finish_call]
        call_index = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_index
            response = responses[min(call_index, len(responses) - 1)]
            call_index += 1
            return response

        mock_sandbox_result = {
            "success": True,
            "stdout": "42\n",
            "stderr": "",
            "exit_code": 0,
            "timed_out": False,
        }

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = mock_generate
            with patch("agent.loop.run_code_sandbox", AsyncMock(return_value=mock_sandbox_result)):
                events = []
                async for event in run_agent(
                    user_input="Run this Python code: print(42)",
                    task_type="coding",
                    model_key="coding",
                ):
                    events.append(event)

        event_types = [e.type for e in events]
        assert "tool_call" in event_types or "finish" in event_types

        finish_events = [e for e in events if e.type == "finish"]
        if finish_events:
            print(f"\n✅ Full Coding Pipeline: {finish_events[0].data['answer']}")
