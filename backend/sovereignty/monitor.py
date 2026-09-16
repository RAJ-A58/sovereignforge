"""
Sovereignty Monitor — reads the mitmproxy network log.

This module is intentionally simple: it reads the log file written by
the mitmproxy addon and exposes helper functions for the FastAPI layer.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MITMPROXY_LOG_PATH, LOCAL_HOSTS


def get_network_log(last_n: int = 50) -> list[dict]:
    """
    Read the last N entries from the mitmproxy network log.

    Returns an empty list if the log file doesn't exist yet
    (mitmproxy may not be running).
    """
    try:
        log_path = Path(MITMPROXY_LOG_PATH)
        if not log_path.exists():
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return entries[-last_n:]

    except (OSError, PermissionError):
        return []


def get_external_call_count() -> int:
    """
    Count how many network calls were blocked (non-local hosts).
    In a sovereign deployment this should always be 0.
    """
    entries = get_network_log(last_n=10_000)
    return sum(1 for e in entries if e.get("blocked", False))


def get_sovereignty_report() -> dict:
    """Full sovereignty summary for the health check endpoint."""
    entries = get_network_log(last_n=10_000)
    total = len(entries)
    blocked = sum(1 for e in entries if e.get("blocked", False))
    local = total - blocked

    hosts = {}
    for e in entries:
        host = e.get("host", "unknown")
        hosts[host] = hosts.get(host, 0) + 1

    return {
        "total_requests": total,
        "local_requests": local,
        "external_blocked": blocked,
        "sovereign": blocked == 0,
        "hosts_contacted": hosts,
    }
