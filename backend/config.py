"""
SovereignForge Configuration
All constants live here. Every other module imports from this file.
Windows-compatible paths using tempfile.gettempdir().
"""
import os
import tempfile
from pathlib import Path

# ── Base directories ──
TEMP_BASE = Path(tempfile.gettempdir()) / "sovereignforge"
UPLOAD_DIR = str(TEMP_BASE / "uploads")
OUTPUT_DIR = str(TEMP_BASE / "outputs")
NETWORK_LOG_PATH = str(TEMP_BASE / "network.log")

# Create dirs on import
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Ollama ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MODELS = {
    # Use quantized versions for 6–8 GB VRAM
    "reasoning": os.getenv("MODEL_REASONING", "qwen2.5:7b-instruct-q4_K_M"),
    "coding":    os.getenv("MODEL_CODING",    "qwen2.5-coder:7b-instruct-q4_K_M"),
    "vision":    os.getenv("MODEL_VISION",    "qwen2.5vl:7b"),
}

# Fallback model names (if quantized not available)
MODELS_FALLBACK = {
    "reasoning": "qwen2.5:7b",
    "coding":    "qwen2.5-coder:7b",
    "vision":    "qwen2.5vl:7b",
}

# ── Task types ──
TASK_TYPES = ["document", "coding", "multimodal"]

# ── Docker sandbox ──
SANDBOX_IMAGE = "sovereignforge-sandbox:latest"
SANDBOX_TIMEOUT = 30          # seconds
SANDBOX_MEMORY_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 500_000_000  # 0.5 CPU (nanocpus)

# ── OCR ──
# Tesseract path — Windows default install location
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
OCR_DPI = 200

# ── mitmproxy ──
MITMPROXY_LOG_PATH = NETWORK_LOG_PATH
MITMPROXY_PORT = 8080

# ── Ports ──
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# ── Agent ──
MAX_AGENT_ITERATIONS = 10
LLM_TIMEOUT_SECONDS = 120   # Ollama can be slow on first load

# ── Allowed local hosts (sovereignty check) ──
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}
