"""
ocr_cache.py — SHA-256 disk cache for OCR results.

Tesseract on a 10-page scanned PDF takes 15-30 seconds.
This cache avoids reprocessing the same file twice:
  - Hash the file bytes with SHA-256
  - Check a JSON index file in TEMP_BASE/ocr_cache/
  - If found, return the cached text immediately
  - If not, let the caller run OCR, then store the result

All storage is local — no external calls.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
import tempfile

# ── Storage ───────────────────────────────────────────────────────────────────
_TEMP_BASE = Path(tempfile.gettempdir()) / "sovereignforge"
CACHE_DIR = _TEMP_BASE / "ocr_cache"
CACHE_INDEX = CACHE_DIR / "index.json"

MAX_CACHE_ENTRIES = 100   # evict oldest when exceeded


def _ensure_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _file_hash(file_path: str) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_index() -> dict:
    """Load the cache index from disk. Returns empty dict on error."""
    _ensure_dir()
    if not CACHE_INDEX.exists():
        return {}
    try:
        with open(CACHE_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_index(index: dict) -> None:
    """Persist the cache index to disk."""
    _ensure_dir()
    with open(CACHE_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def get_cached_ocr(file_path: str) -> dict | None:
    """
    Look up OCR result for a file by its SHA-256 hash.
    Returns the cached result dict if found, otherwise None.
    """
    try:
        file_hash = _file_hash(file_path)
    except OSError:
        return None

    index = _load_index()
    entry = index.get(file_hash)
    if not entry:
        return None

    # Load the cached text file
    text_file = CACHE_DIR / f"{file_hash}.txt"
    if not text_file.exists():
        return None

    try:
        with open(text_file, "r", encoding="utf-8") as f:
            text = f.read()
        return {
            "success": True,
            "text": text,
            "pages": entry.get("pages", 1),
            "error": None,
            "cache_hit": True,
        }
    except OSError:
        return None


def put_cached_ocr(file_path: str, result: dict) -> None:
    """
    Store an OCR result in the disk cache.
    Only stores successful results.
    """
    if not result.get("success"):
        return

    try:
        file_hash = _file_hash(file_path)
    except OSError:
        return

    _ensure_dir()
    index = _load_index()

    # Write the text to a dedicated file
    text_file = CACHE_DIR / f"{file_hash}.txt"
    try:
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(result.get("text", ""))
    except OSError:
        return

    index[file_hash] = {
        "file_path": file_path,
        "pages": result.get("pages", 1),
        "cached_at": time.time(),
    }

    # LRU eviction: remove oldest entries
    if len(index) > MAX_CACHE_ENTRIES:
        sorted_keys = sorted(index, key=lambda k: index[k].get("cached_at", 0))
        for old_key in sorted_keys[:len(index) - MAX_CACHE_ENTRIES]:
            old_file = CACHE_DIR / f"{old_key}.txt"
            old_file.unlink(missing_ok=True)
            del index[old_key]

    _save_index(index)


def get_cache_stats() -> dict:
    """Return OCR cache statistics for the /health endpoint."""
    index = _load_index()
    return {
        "entries": len(index),
        "max_entries": MAX_CACHE_ENTRIES,
        "cache_dir": str(CACHE_DIR),
    }
