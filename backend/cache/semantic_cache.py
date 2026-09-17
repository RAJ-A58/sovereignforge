"""
semantic_cache.py — In-memory semantic LLM response cache for SovereignForge.

How it works:
  - Every LLM call's prompt is embedded with sentence-transformers (all-MiniLM-L6-v2)
  - Cosine similarity is checked against all cached (prompt_embedding, response) pairs
  - If similarity >= SIMILARITY_THRESHOLD (0.92), the cached response is returned instantly
  - Cache is LRU-capped at MAX_CACHE_SIZE entries to bound memory usage
  - 100% offline — uses the same embedding model already used by the knowledge base
"""
from __future__ import annotations

import time
import hashlib
from collections import OrderedDict
from typing import Optional

import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.92   # cosine similarity above which we return cache hit
MAX_CACHE_SIZE = 200          # max entries before LRU eviction
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # same model used by knowledge_base.py

_embedder = None  # lazy-loaded singleton


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _embed(text: str) -> list[float]:
    """Return embedding vector for a text string."""
    return _get_embedder().encode(text, convert_to_tensor=False).tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    """NumPy cosine similarity between two equal-length vectors."""
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


class SemanticCache:
    """
    Thread-safe (asyncio-compatible) semantic LRU cache for LLM responses.
    Key = (model_key, prompt_embedding). Value = (response_str, metadata).
    """

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        max_size: int = MAX_CACHE_SIZE,
    ):
        self.threshold = similarity_threshold
        self.max_size = max_size
        # OrderedDict for O(1) LRU: key = sha256(model_key+prompt[:64]), value = (embedding, response, meta)
        self._store: OrderedDict[str, tuple[list[float], str, dict]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, model_key: str, prompt: str) -> Optional[str]:
        """
        Look up a cached response.
        Returns the cached response string if a semantic near-match is found,
        otherwise returns None (caller must call the LLM).
        """
        try:
            query_emb = _embed(prompt)
        except Exception:
            return None  # embedding failed — fall through to LLM

        best_score = 0.0
        best_key: Optional[str] = None

        for cache_key, (stored_emb, _, meta) in self._store.items():
            if meta.get("model_key") != model_key:
                continue
            score = _cosine(query_emb, stored_emb)
            if score > best_score:
                best_score = score
                best_key = cache_key

        if best_score >= self.threshold and best_key:
            # LRU: move to end
            self._store.move_to_end(best_key)
            _, response, _ = self._store[best_key]
            self.hits += 1
            return response

        self.misses += 1
        return None

    def put(self, model_key: str, prompt: str, response: str) -> None:
        """
        Store a (prompt, response) pair in the cache.
        Evicts the least-recently-used entry when max_size is reached.
        """
        try:
            emb = _embed(prompt)
        except Exception:
            return  # embedding failed — don't cache, silently continue

        cache_key = hashlib.sha256(f"{model_key}:{prompt[:128]}".encode()).hexdigest()

        self._store[cache_key] = (
            emb,
            response,
            {
                "model_key": model_key,
                "cached_at": time.time(),
                "prompt_preview": prompt[:80],
            },
        )
        self._store.move_to_end(cache_key)

        # LRU eviction
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def stats(self) -> dict:
        """Return cache statistics for the /health endpoint."""
        total = self.hits + self.misses
        return {
            "entries": len(self._store),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
            "threshold": self.threshold,
        }

    def clear(self) -> None:
        """Clear all cache entries (useful for testing or manual reset)."""
        self._store.clear()
        self.hits = 0
        self.misses = 0


# ── Module-level singleton — import this from registry.py ──
cache = SemanticCache()
