"""Model registry — single point of contact for all Ollama calls."""
import httpx
import base64
import sys
import os
from pathlib import Path

# Allow running from backend/ directory directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OLLAMA_BASE_URL, MODELS, MODELS_FALLBACK, LLM_TIMEOUT_SECONDS


class ModelRegistry:
    """
    Central client for all Ollama model calls.
    Never call Ollama directly from tools — always go through this registry.
    """

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.models = MODELS
        self.fallback = MODELS_FALLBACK

    async def generate(
        self,
        model_key: str,
        prompt: str,
        system: str = None,
        stream: bool = False,
    ) -> str:
        """
        Call a text/reasoning model.

        Args:
            model_key: "reasoning" | "coding" | "vision"
            prompt:    The user-facing prompt
            system:    Optional system prompt override
            stream:    Not used yet — streaming handled at WebSocket layer

        Returns:
            Full response string from the model.
        """
        model_name = self._resolve_model(model_key)

        payload: dict = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def generate_vision(self, prompt: str, image_path: str) -> str:
        """
        Call the vision model with a local image file.

        Args:
            prompt:     Description / question about the image
            image_path: Absolute path to a .jpg/.png file

        Returns:
            Model analysis string.
        """
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        payload: dict = {
            "model": self._resolve_model("vision"),
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def health_check(self) -> dict:
        """Return list of locally available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return {"status": "ok", "models": resp.json().get("models", [])}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _resolve_model(self, model_key: str) -> str:
        """Return model name string for the given key."""
        if model_key not in self.models:
            raise ValueError(f"Unknown model key: {model_key!r}. "
                             f"Valid keys: {list(self.models.keys())}")
        return self.models[model_key]


# ── Singleton — import this from everywhere ──
registry = ModelRegistry()
