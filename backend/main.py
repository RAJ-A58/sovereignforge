"""
SovereignForge FastAPI Backend

Endpoints:
  POST /upload              — upload a file, get back its server path
  WS   /ws/agent            — main agent WebSocket (stream events)
  WS   /ws/network          — network monitor log feed
  GET  /download/{filename} — download generated output files
  GET  /health              — health check + model availability
  GET  /api/classify        — classify a task without running the agent
"""
import sys
import os
import uuid
import asyncio
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect,
    UploadFile, File, HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import aiofiles

from router.task_router import classify_task
from agent.loop import run_agent
from models.registry import registry
from sovereignty.monitor import get_network_log, get_external_call_count
from tools.knowledge_base import (
    get_kb_stats, ingest_text, search_knowledge_base, clear_knowledge_base, run_ingest_file
)
from guardrails.input_guard import check_user_input, GuardViolation
from schemas import AgentEvent, UploadResponse
from config import UPLOAD_DIR, OUTPUT_DIR, FRONTEND_PORT

# ─────────────────────────────────────────────────────────────────────────────
#  App setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SovereignForge API",
    description="Sovereign on-premise agentic AI workbench",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{FRONTEND_PORT}",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  File Upload
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the server.
    Returns the server-side file_path to use in agent tasks.
    """
    file_id = str(uuid.uuid4())
    original_name = file.filename or "upload"
    ext = Path(original_name).suffix.lower()
    safe_name = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    async with aiofiles.open(save_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return UploadResponse(
        file_id=file_id,
        file_path=save_path,
        filename=original_name,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Main Agent WebSocket
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    Bi-directional WebSocket for agent task execution.

    Client sends JSON: {"user_input": "...", "file_path": null}
    Server streams:    AgentEvent JSON objects until finish/error
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            user_input: str = data.get("user_input", "").strip()
            file_path: str | None = data.get("file_path")

            if not user_input:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "user_input is required"},
                })
                continue

            # Validate file path if provided
            if file_path and not Path(file_path).exists():
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"File not found: {file_path}"},
                })
                continue

            # ── Input guardrail check ──────────────────────────────────────────
            try:
                check_user_input(user_input)
            except GuardViolation as gv:
                await websocket.send_json({
                    "type": "guardrail_block",
                    "data": {
                        "category": gv.category,
                        "message": gv.reason,
                    },
                })
                continue

            # Classify the task
            classification = classify_task(user_input, file_path)
            await websocket.send_json({
                "type": "classified",
                "data": classification,
            })

            # Stream agent events
            async for event in run_agent(
                user_input=user_input,
                task_type=classification["task_type"],
                model_key=classification["model_key"],
                file_path=file_path,
            ):
                await websocket.send_json(event.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(exc)},
            })
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Network Monitor WebSocket
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/network")
async def network_monitor_websocket(websocket: WebSocket):
    """
    Streams the mitmproxy network log to the UI every second.
    Shows which hosts were contacted — should always be localhost only.
    """
    await websocket.accept()
    last_count = 0

    try:
        while True:
            entries = get_network_log(last_n=100)
            external_count = get_external_call_count()

            await websocket.send_json({
                "entries": entries,
                "total": len(entries),
                "external_blocked": external_count,
                "sovereign": external_count == 0,
            })
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  File Download
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated output file (e.g., .docx)."""
    # Security: prevent path traversal
    safe_filename = Path(filename).name
    file_path = os.path.join(OUTPUT_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/octet-stream",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Classification endpoint (REST)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/classify")
async def classify_endpoint(user_input: str, file_path: str = None):
    """Classify a task without running the agent."""
    return classify_task(user_input, file_path)


# ─────────────────────────────────────────────────────────────────────────────
#  Knowledge Base endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/kb/stats")
async def kb_stats():
    """Return knowledge base statistics."""
    return get_kb_stats()


@app.post("/api/kb/ingest-file")
async def kb_ingest_file(file: UploadFile = File(...), doc_type: str = "document"):
    """Upload and ingest a file into the knowledge base."""
    file_id = str(uuid.uuid4())
    original_name = file.filename or "upload"
    ext = Path(original_name).suffix.lower()
    safe_name = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    async with aiofiles.open(save_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    result = await run_ingest_file(save_path, source_name=original_name, doc_type=doc_type)
    return result


@app.post("/api/kb/ingest-text")
async def kb_ingest_text(body: dict):
    """Ingest raw text into the knowledge base."""
    text = body.get("text", "")
    source = body.get("source_name", "manual_entry")
    doc_type = body.get("doc_type", "document")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, ingest_text, text, source, doc_type)
    return result


@app.get("/api/kb/search")
async def kb_search(query: str, n_results: int = 5):
    """Search the knowledge base."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_knowledge_base, query, n_results)


@app.delete("/api/kb/clear")
async def kb_clear():
    """Clear all documents from the knowledge base."""
    return clear_knowledge_base()


# ─────────────────────────────────────────────────────────────────────────────
#  Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — returns model availability, sovereignty status, KB stats, and cache stats."""
    model_status = await registry.health_check()
    external_calls = get_external_call_count()
    kb = get_kb_stats()

    # Import cache stats (lazy import avoids circular dependency)
    from cache.semantic_cache import cache as _sem_cache
    from cache.ocr_cache import get_cache_stats as _ocr_stats

    return {
        "status": "ok",
        "sovereign": True,
        "external_calls_blocked": external_calls,
        "models": model_status,
        "knowledge_base": {
            "ready": kb["ready"],
            "total_chunks": kb["total_chunks"],
            "sources": list(kb["sources"].keys()),
        },
        "cache": {
            "semantic_llm": _sem_cache.stats(),
            "ocr": _ocr_stats(),
        },
        "upload_dir": UPLOAD_DIR,
        "output_dir": OUTPUT_DIR,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Run directly
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    from config import BACKEND_PORT
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)
