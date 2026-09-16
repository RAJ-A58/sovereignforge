# sovereignty/mitmproxy_addon.py
# Run with:  mitmdump --listen-port 8080 -s sovereignty/mitmproxy_addon.py
#
# This addon:
#   1. Intercepts every outbound HTTP request
#   2. Logs it to a JSON file
#   3. BLOCKS any request going to non-local hosts
#   4. Allows all localhost / 127.0.0.1 traffic (e.g., Ollama on :11434)
import json
from datetime import datetime
from mitmproxy import http

# Where to write the log — must match config.py MITMPROXY_LOG_PATH
# Windows: use forward slashes or raw string
import os
import tempfile

LOG_FILE = os.path.join(tempfile.gettempdir(), "sovereignforge", "network.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}


class SovereigntyMonitor:
    def __init__(self):
        # Clear log on (re)start
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print(f"[SovereignForge] Sovereignty monitor active. Log: {LOG_FILE}")

    def request(self, flow: http.HTTPFlow) -> None:
        """Called for every outbound HTTP/HTTPS request."""
        host = flow.request.host
        is_local = self._is_local(host)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": flow.request.method,
            "host": host,
            "port": flow.request.port,
            "url": flow.request.pretty_url[:200],  # truncate long URLs
            "is_local": is_local,
            "blocked": not is_local,
        }

        # Block all non-local traffic
        if not is_local:
            flow.response = http.Response.make(
                403,
                b"BLOCKED: SovereignForge sovereignty monitor — no external calls allowed",
                {"Content-Type": "text/plain"},
            )
            print(f"[BLOCKED] {flow.request.method} {host}")
        else:
            print(f"[LOCAL]   {flow.request.method} {host}:{flow.request.port}")

        # Append to log
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    def _is_local(self, host: str) -> bool:
        return any(h in host for h in LOCAL_HOSTS)


addons = [SovereigntyMonitor()]
