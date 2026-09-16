"""
Code Sandbox Tool — execute Python code inside an isolated Docker container.

Security model:
  - No network access (--network=none)
  - Memory capped at 256MB
  - CPU capped at 0.5 cores
  - Read-only filesystem (code injected via volume mount)
  - Container auto-deleted after run
  - Hard 30-second timeout
"""
import sys
import asyncio
import tempfile
import os
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SANDBOX_IMAGE,
    SANDBOX_TIMEOUT,
    SANDBOX_MEMORY_LIMIT,
    SANDBOX_CPU_QUOTA,
)

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


async def run_code_sandbox(code: str, language: str = "python") -> dict:
    """
    Execute code in an isolated Docker container.

    Args:
        code:     Python source code string to execute
        language: Currently only "python" is supported

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "timed_out": bool
        }
    """
    if not DOCKER_AVAILABLE:
        return _failure("docker Python SDK not installed. Run: pip install docker")

    if language.lower() != "python":
        return _failure(f"Language '{language}' not yet supported. Only 'python' is available.")

    # Write code to a temp directory (will be volume-mounted read-only)
    tmp_dir = tempfile.mkdtemp(prefix="sfbox_")
    code_file = os.path.join(tmp_dir, "solution.py")

    try:
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _run_container, tmp_dir),
                timeout=SANDBOX_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {SANDBOX_TIMEOUT} seconds",
                "exit_code": -1,
                "timed_out": True,
            }
        return result

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_container(tmp_dir: str) -> dict:
    """Synchronous Docker run — called in thread executor."""
    try:
        client = docker.from_env()

        # Determine the bind path for the volume
        # On Windows, Docker Desktop requires forward-slash paths
        bind_path = _to_docker_path(tmp_dir)

        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command="python3 /sandbox/solution.py",
            volumes={bind_path: {"bind": "/sandbox", "mode": "ro"}},
            network_mode="none",         # ← ZERO network access
            mem_limit=SANDBOX_MEMORY_LIMIT,
            nano_cpus=SANDBOX_CPU_QUOTA,
            read_only=True,
            tmpfs={"/tmp": "size=64m"},
            remove=True,                 # auto-delete after run
            detach=False,
            stdout=True,
            stderr=True,
        )

        # When detach=False, .run() returns bytes (combined stdout+stderr)
        output = container.decode("utf-8", errors="replace") if container else ""

        return {
            "success": True,
            "stdout": output,
            "stderr": "",
            "exit_code": 0,
            "timed_out": False,
        }

    except docker.errors.ContainerError as exc:
        # Code executed but returned non-zero exit code (e.g. syntax error)
        return {
            "success": False,
            "stdout": "",
            "stderr": getattr(exc, "stderr", b"").decode("utf-8", errors="replace") if hasattr(exc, "stderr") and getattr(exc, "stderr", None) else str(exc),
            "exit_code": exc.exit_status,
            "timed_out": False,
        }

    except docker.errors.ImageNotFound:
        return _failure(
            f"Sandbox image '{SANDBOX_IMAGE}' not found. "
            "Run: docker build -t sovereignforge-sandbox:latest ./sandbox/"
        )

    except Exception as exc:
        timed_out = "timeout" in str(exc).lower() or "timed out" in str(exc).lower()
        return {
            "success": False,
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "timed_out": timed_out,
        }


def _failure(message: str) -> dict:
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "exit_code": -1,
        "timed_out": False,
    }


def _to_docker_path(win_path: str) -> str:
    """
    Convert Windows path to Docker-compatible path.
    e.g.  C:\\Users\\foo\\tmp  →  C:/Users/foo/tmp
    """
    return win_path.replace("\\", "/")
