#!/usr/bin/env python3
"""Bootstrap HTTP для GL-MT6000 Flint 2 (порт 8789)."""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = Path("/root/.xkeen-router-access.token")
AUTH_KEYS = Path("/root/.ssh/authorized_keys")
MARKER = "# flint2-router-tunnel"
TUN_PORT = 6223
_RATE: dict[str, list[float]] = defaultdict(list)
_RATE_MAX = 120  # requests per hour per IP for GET


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _rate_ok(self) -> bool:
        ip = self.client_address[0]
        now = time.time()
        window = _RATE[ip]
        _RATE[ip] = [t for t in window if now - t < 3600]
        if len(_RATE[ip]) >= _RATE_MAX:
            return False
        _RATE[ip].append(now)
        return True

    def do_GET(self):
        if self.path.startswith("/register"):
            self.send_error(404)
            return
        if not self._rate_ok():
            self.send_error(429, "rate limit")
            return
        return super().do_GET()

    def do_POST(self):
        if self.path != "/register-router-key":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "bad json")
            return
        token = str(data.get("token", ""))
        pubkey = str(data.get("pubkey", "")).strip()
        expected = TOKEN_FILE.read_text().strip() if TOKEN_FILE.is_file() else ""
        if not expected or token != expected:
            self.send_error(403, "forbidden")
            return
        if not pubkey.startswith("ssh-") or "\n" in pubkey:
            self.send_error(400, "bad pubkey")
            return
        line = (
            f'restrict,port-forwarding,permitlisten="127.0.0.1:{TUN_PORT}",'
            f'no-pty,no-agent-forwarding {pubkey} {MARKER}\n'
        )
        existing = AUTH_KEYS.read_text() if AUTH_KEYS.is_file() else ""
        cleaned = [ln for ln in existing.splitlines(True) if MARKER not in ln]
        cleaned.append(line)
        AUTH_KEYS.write_text("".join(cleaned))
        os.chmod(AUTH_KEYS, 0o600)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}\n')

    def log_message(self, fmt, *args):
        try:
            with open("/tmp/flint2-bootstrap-hits.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {self.client_address[0]} {self.command} {self.path}\n")
        except OSError:
            pass
        if self.path.startswith("/register"):
            super().log_message(fmt, *args)


def main():
    host, port = "0.0.0.0", 8789
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"flint2 bootstrap: {ROOT} on {host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
