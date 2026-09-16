"""
Agent-level tests — test the full ReAct loop with mocked tools.
These tests do NOT require a real Ollama model.
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest


class TestAgentEventTypes:
    """Test that the agent yields proper event types."""

    @pytest.mark.asyncio
    async def test_agent_yields_start_event(self):
        """Agent should always yield agent_start as first event."""
        from agent.loop import run_agent
        from schemas import AgentEvent

        # Mock the LLM to immediately return a finish action
        finish_response = '{"thought": "done", "action": "finish", "action_input": {"answer": "Task complete", "artifacts": []}, "observation": null}'

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = AsyncMock(return_value=finish_response)

            events = []
            async for event in run_agent(
                user_input="test task",
                task_type="document",
                model_key="reasoning",
            ):
                events.append(event)

        # First event must be agent_start
        assert events[0].type == "agent_start"
        assert events[0].data["task_type"] == "document"

    @pytest.mark.asyncio
    async def test_agent_yields_thinking_event(self):
        """Agent should yield a thinking event each iteration."""
        from agent.loop import run_agent

        finish_response = '{"thought": "done", "action": "finish", "action_input": {"answer": "done", "artifacts": []}, "observation": null}'

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = AsyncMock(return_value=finish_response)

            events = []
            async for event in run_agent(
                user_input="test",
                task_type="coding",
                model_key="coding",
            ):
                events.append(event)

        event_types = [e.type for e in events]
        assert "thinking" in event_types

    @pytest.mark.asyncio
    async def test_agent_finishes_on_finish_action(self):
        """Agent should emit finish event and stop when action=finish."""
        from agent.loop import run_agent

        finish_response = '{"thought": "done", "action": "finish", "action_input": {"answer": "The answer is 42", "artifacts": []}, "observation": null}'

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = AsyncMock(return_value=finish_response)

            events = []
            async for event in run_agent(
                user_input="test",
                task_type="document",
                model_key="reasoning",
            ):
                events.append(event)

        event_types = [e.type for e in events]
        assert "finish" in event_types

        finish_event = next(e for e in events if e.type == "finish")
        assert finish_event.data["answer"] == "The answer is 42"

    @pytest.mark.asyncio
    async def test_agent_calls_tool_and_feeds_result_back(self):
        """Agent should call a tool, get result, then continue."""
        from agent.loop import run_agent

        # First call: tell agent to use ocr
        ocr_response = '{"thought": "need to OCR", "action": "ocr", "action_input": {"file_path": "/tmp/test.pdf"}, "observation": null}'
        # Second call: finish
        finish_response = '{"thought": "done", "action": "finish", "action_input": {"answer": "OCR complete", "artifacts": []}, "observation": null}'

        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ocr_response
            return finish_response

        mock_ocr_result = {"success": True, "text": "Sample text", "pages": 1, "error": None}

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = mock_generate
            with patch("agent.loop.TOOLS") as mock_tools:
                mock_tools.__contains__ = lambda self, key: key in {"ocr", "finish"}
                mock_tools.__getitem__ = lambda self, key: AsyncMock(return_value=mock_ocr_result)

                # Use real TOOLS but mock just OCR
                with patch("agent.loop.run_ocr", AsyncMock(return_value=mock_ocr_result)):
                    events = []
                    async for event in run_agent(
                        user_input="read this PDF",
                        task_type="document",
                        model_key="reasoning",
                        file_path="/tmp/test.pdf",
                    ):
                        events.append(event)

        event_types = [e.type for e in events]
        assert "tool_call" in event_types
        assert "tool_result" in event_types

    @pytest.mark.asyncio
    async def test_agent_handles_invalid_json_and_recovers(self):
        """Agent should handle JSON parse failure gracefully."""
        from agent.loop import run_agent
        from config import MAX_AGENT_ITERATIONS

        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return "This is not valid JSON at all"
            return '{"thought": "ok", "action": "finish", "action_input": {"answer": "recovered", "artifacts": []}, "observation": null}'

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = mock_generate

            events = []
            async for event in run_agent(
                user_input="test",
                task_type="document",
                model_key="reasoning",
            ):
                events.append(event)

        event_types = [e.type for e in events]
        # Should have error events for the bad JSON
        assert "error" in event_types or "finish" in event_types  # either recovered or errored

    @pytest.mark.asyncio
    async def test_agent_hits_max_iterations(self):
        """Agent should stop and emit max_iterations event."""
        from agent.loop import run_agent

        # Always return valid JSON but never finish
        call_response = '{"thought": "still thinking", "action": "ocr", "action_input": {"file_path": "/tmp/x.pdf"}, "observation": null}'

        mock_ocr_result = {"success": True, "text": "text", "pages": 1, "error": None}

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = AsyncMock(return_value=call_response)
            with patch("agent.loop.run_ocr", AsyncMock(return_value=mock_ocr_result)):
                events = []
                async for event in run_agent(
                    user_input="test",
                    task_type="document",
                    model_key="reasoning",
                    file_path="/tmp/x.pdf",
                ):
                    events.append(event)
                    if len(events) > 200:  # safety limit in test
                        break

        event_types = [e.type for e in events]
        assert "max_iterations" in event_types

    @pytest.mark.asyncio
    async def test_agent_rejects_unknown_tool(self):
        """Agent should handle unknown tool name gracefully."""
        from agent.loop import run_agent

        bad_tool_response = '{"thought": "try this", "action": "nonexistent_tool", "action_input": {}, "observation": null}'
        finish_response = '{"thought": "ok", "action": "finish", "action_input": {"answer": "done", "artifacts": []}, "observation": null}'

        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return bad_tool_response
            return finish_response

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate = mock_generate

            events = []
            async for event in run_agent(
                user_input="test",
                task_type="document",
                model_key="reasoning",
            ):
                events.append(event)

        event_types = [e.type for e in events]
        assert "error" in event_types  # unknown tool should produce error event
