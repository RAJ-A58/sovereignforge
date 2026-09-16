"""Task Router — classify user input into task type using heuristics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TASK_TYPES

# ── Keyword Banks ──

DOCUMENT_KEYWORDS = [
    "report", "document", "pdf", "scan", "extract", "summarize",
    "approval", "note", "findings", "review", "analyze this file",
    "read this", "what does this say", "invoice", "letter", "contract",
    "memo", "brief", "assessment", "audit", "compliance", "policy",
    "draft", "word document", "docx",
]

CODING_KEYWORDS = [
    "write code", "python", "function", "script", "debug", "fix this code",
    "implement", "algorithm", "program", "class", "error in", "run this",
    "execute", "sort", "parse", "calculate", "compute", "bug", "syntax",
    "compile", "loop", "recursive", "data structure", "api", "json",
    "regex", "test", "unit test", "refactor", "optimize",
]

MULTIMODAL_KEYWORDS = [
    "image", "photo", "picture", "diagram", "chart", "what is in",
    "describe this", "identify", "detect", "screenshot", "drawing",
    "handwritten", "figure", "table in image", "scan", "ocr image",
    "visual", "look at", "analyze this image", "read this image",
]

# Map task type → Ollama model key
MODEL_MAP = {
    "document":   "reasoning",
    "coding":     "coding",
    "multimodal": "vision",
}

# File extension → (task_type, model_key, confidence)
EXTENSION_MAP = {
    ".pdf":  ("document",   "reasoning", 0.95),
    ".docx": ("document",   "reasoning", 0.95),
    ".doc":  ("document",   "reasoning", 0.90),
    ".txt":  ("document",   "reasoning", 0.85),
    ".rtf":  ("document",   "reasoning", 0.85),
    ".jpg":  ("multimodal", "vision",    0.90),
    ".jpeg": ("multimodal", "vision",    0.90),
    ".png":  ("multimodal", "vision",    0.90),
    ".webp": ("multimodal", "vision",    0.90),
    ".bmp":  ("multimodal", "vision",    0.85),
    ".tiff": ("multimodal", "vision",    0.85),
    ".tif":  ("multimodal", "vision",    0.85),
    ".py":   ("coding",     "coding",    0.95),
    ".js":   ("coding",     "coding",    0.95),
    ".ts":   ("coding",     "coding",    0.95),
    ".cpp":  ("coding",     "coding",    0.95),
    ".java": ("coding",     "coding",    0.95),
    ".c":    ("coding",     "coding",    0.95),
    ".go":   ("coding",     "coding",    0.95),
    ".rs":   ("coding",     "coding",    0.95),
    ".sh":   ("coding",     "coding",    0.90),
}


def classify_task(user_input: str, file_path: str = None) -> dict:
    """
    Classify a user request into a task type.

    Args:
        user_input: Raw user text / prompt
        file_path:  Optional file path that was uploaded

    Returns:
        {
            "task_type":  "document" | "coding" | "multimodal",
            "confidence": float  (0.0 – 1.0),
            "model_key":  "reasoning" | "coding" | "vision",
            "reasoning":  str  (human-readable explanation)
        }
    """
    text = user_input.lower().strip()

    # ── 1. File extension is the strongest signal ──
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext in EXTENSION_MAP:
            task_type, model_key, confidence = EXTENSION_MAP[ext]

            # Special case: image + coding question → still coding
            if task_type == "multimodal":
                code_score = sum(1 for k in CODING_KEYWORDS if k in text)
                if code_score >= 2:
                    return _result("coding", 0.80, "coding",
                                   f"Image file with {code_score} coding keywords → coding task")

            return _result(task_type, confidence, model_key,
                           f"File extension '{ext}' → {task_type} task")

    # ── 2. Keyword scoring ──
    doc_score  = sum(1 for k in DOCUMENT_KEYWORDS   if k in text)
    code_score = sum(1 for k in CODING_KEYWORDS     if k in text)
    mm_score   = sum(1 for k in MULTIMODAL_KEYWORDS if k in text)

    scores = {
        "document":   doc_score,
        "coding":     code_score,
        "multimodal": mm_score,
    }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        # No signal → default to reasoning/document
        return _result("document", 0.40, "reasoning",
                       "No strong keyword signal — defaulting to document/reasoning")

    confidence = min(0.50 + best_score * 0.10, 0.95)

    return _result(
        best_type,
        confidence,
        MODEL_MAP[best_type],
        f"Keyword scores {scores} → '{best_type}' wins with score {best_score}",
    )


def _result(task_type: str, confidence: float, model_key: str, reasoning: str) -> dict:
    return {
        "task_type":  task_type,
        "confidence": round(confidence, 2),
        "model_key":  model_key,
        "reasoning":  reasoning,
    }
