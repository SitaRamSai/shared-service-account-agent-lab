#!/usr/bin/env python3
"""Zero-dependency local server for the episode 1 UI.

Run from anywhere:  python3 ui/server.py
Then open http://127.0.0.1:8000 and press "Run demo".
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent
ROOT = UI_DIR.parent
TICKET_RE = re.compile(r"\bT-\d+\b")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:  # keep the console readable
        sys.stderr.write("ui: " + (format % args) + "\n")

    def _send(self, body: bytes, status: int = 200, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path in ("/", "/index.html"):
            self._send((UI_DIR / "index.html").read_bytes(), ctype="text/html; charset=utf-8")
        elif self.path == "/demo.py":
            self._send((ROOT / "demo.py").read_bytes(), ctype="text/plain; charset=utf-8")
        else:
            self._send(b'{"error":"not found"}', status=404)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path != "/api/run":
            return self._send(b'{"error":"not found"}', status=404)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(b'{"error":"bad json"}', status=400)

        authz = bool(payload.get("authz"))
        proc = subprocess.run(
            [sys.executable, str(ROOT / "demo.py"), "--mode", "after" if authz else "before"],
            capture_output=True,
            text=True,
        )
        output = proc.stdout
        if proc.stderr.strip():
            output += "\n[stderr]\n" + proc.stderr
        tickets = TICKET_RE.findall(output)
        verdict = "denied" if "WRITE FAILED" in output else ("created" if tickets else "error")
        self._send(
            json.dumps(
                {
                    "output": output,
                    "verdict": verdict,
                    "ticket": tickets[0] if tickets else None,
                    "authz": authz,
                    "returncode": proc.returncode,
                }
            ).encode()
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Episode 1 UI server (no dependencies).")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"episode 1 UI on http://{args.host}:{args.port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
