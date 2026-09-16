"""Extract Tool — use LLM to extract structured information from raw text."""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import registry

EXTRACT_SYSTEM_PROMPT = (
    "You are a precise document analysis assistant. "
    "Extract structured information exactly as requested. "
    "Always respond with valid JSON only. "
    "No preamble, no explanation, no markdown fences."
)

# Max chars to send to LLM to stay within context window
MAX_TEXT_LENGTH = 6000


async def run_extract(
    raw_text: str,
    extraction_goal: str = "key findings, risks, and recommendations",
) -> dict:
    """
    Extract structured information from raw text using the reasoning LLM.

    Args:
        raw_text:         The source text (e.g., from OCR)
        extraction_goal:  Human description of what to pull out

    Returns:
        {
            "success": bool,
            "summary": str,
            "findings": list[str],
            "risks": list[str],
            "recommendations": list[str],
            "raw_json": dict
        }
    """
    truncated = raw_text[:MAX_TEXT_LENGTH]
    if len(raw_text) > MAX_TEXT_LENGTH:
        truncated += f"\n\n[... {len(raw_text) - MAX_TEXT_LENGTH} characters truncated ...]"

    prompt = f"""Extract the following from this document text: {extraction_goal}

DOCUMENT TEXT:
{truncated}

Respond ONLY with a valid JSON object with these exact keys:
{{
  "summary": "2-3 sentence overview of the document",
  "findings": ["finding 1", "finding 2"],
  "risks": ["risk 1", "risk 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

No other text. No markdown. Just the JSON object."""

    try:
        response = await registry.generate(
            "reasoning",
            prompt,
            system=EXTRACT_SYSTEM_PROMPT,
        )
    except Exception as exc:
        return _failure(str(exc))

    return _parse_response(response)


def _parse_response(response: str) -> dict:
    """Parse LLM JSON response with robust fallback handling."""
    # Try direct JSON parse
    try:
        clean = response.strip()
        parsed = json.loads(clean)
        return _build_success(parsed)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", response).strip()
    try:
        parsed = json.loads(clean)
        return _build_success(parsed)
    except json.JSONDecodeError:
        pass

    # Find first JSON object in string
    match = re.search(r"\{[\s\S]*\}", response)
    if match:
        try:
            parsed = json.loads(match.group())
            return _build_success(parsed)
        except json.JSONDecodeError:
            pass

    # Complete fallback — return raw text as single finding
    return {
        "success": False,
        "summary": response[:300],
        "findings": [response] if response else [],
        "risks": [],
        "recommendations": [],
        "raw_json": {},
        "error": "Failed to parse LLM JSON response",
    }


def _build_success(parsed: dict) -> dict:
    return {
        "success": True,
        "summary": parsed.get("summary", ""),
        "findings": _ensure_list(parsed.get("findings", [])),
        "risks": _ensure_list(parsed.get("risks", [])),
        "recommendations": _ensure_list(parsed.get("recommendations", [])),
        "raw_json": parsed,
    }


def _failure(error: str) -> dict:
    return {
        "success": False,
        "summary": "",
        "findings": [],
        "risks": [],
        "recommendations": [],
        "raw_json": {},
        "error": error,
    }


def _ensure_list(val) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []
