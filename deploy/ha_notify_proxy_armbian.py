#!/usr/bin/env python3
"""Локальный прокси на armbian: POST от HA → GET на VPS (без aiohttp)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# Tailscale VPS (после tailscale up на armbian) или публичный IP:
VPS_URL = os.getenv(
    "VPS_NOTIFY_URL", "http://100.84.19.35:8877/notify"
)
TOKEN = os.getenv("HA_NOTIFY_TOKEN", "")
PORT = int(os.getenv("HA_PROXY_PORT", "8766"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _check_auth(self) -> bool:
        if not TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {TOKEN}"

    def do_GET(self) -> None:
        if self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/notify":
            self.send_response(404)
            self.end_headers()
            return
        if not self._check_auth():
            self.send_response(401)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            message = (body.get("message") or "").strip()
        except Exception:
            self.send_response(400)
            self.end_headers()
            return
        if not message:
            self.send_response(400)
            self.end_headers()
            return
        q = urllib.parse.urlencode({"message": message})
        url = f"{VPS_URL}?{q}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {TOKEN}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code)
            self.end_headers()
            self.wfile.write(exc.read())
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())


def main() -> None:
    print(f"proxy :{PORT} -> GET {VPS_URL}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
