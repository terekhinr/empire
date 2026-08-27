#!/usr/bin/env python3
"""VPS proxy → Flint empire-api через reverse SSH :6223.

Слушает 127.0.0.1:8767. Nginx /home-ops/ → сюда.
Токен тот же, что на Flint (/etc/empire/flint-ui.token).
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = Path(os.getenv("EMPIRE_FLINT_UI_TOKEN", "/etc/empire/flint-ui.token"))
WWW = ROOT / "scripts/flint2/empire-flint-watchdog/www"
LISTEN = ("127.0.0.1", int(os.getenv("EMPIRE_HOME_OPS_PORT", "8767")))
SSH = [
    "ssh",
    "-p",
    "6223",
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=12",
    "-o",
    "StrictHostKeyChecking=accept-new",
    "root@127.0.0.1",
]


def load_token() -> str:
    if TOKEN_FILE.is_file():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    return ""


def flint_api(action: str, token: str, svc: str = "") -> tuple[int, bytes]:
    q = urllib.parse.urlencode({"action": action, "token": token, "svc": svc})
    # wget on OpenWrt
    remote = f"wget -qO- 'http://127.0.0.1/cgi-bin/empire-api?{q}'"
    try:
        p = subprocess.run(
            SSH + [remote],
            capture_output=True,
            timeout=90,
        )
        body = p.stdout or p.stderr or b'{"ok":false,"error":"empty"}'
        if p.returncode != 0 and not p.stdout:
            return 502, json.dumps({"ok": False, "error": "ssh_fail", "detail": (p.stderr or b"").decode()[:200]}).encode()
        return 200, body
    except subprocess.TimeoutExpired:
        return 504, b'{"ok":false,"error":"timeout"}'
    except Exception as exc:
        return 500, json.dumps({"ok": False, "error": str(exc)}).encode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[home-ops] {self.address_string()} {fmt % args}")

    def _token_ok(self) -> bool:
        expected = load_token()
        if not expected:
            return False
        auth = self.headers.get("Authorization", "")
        got = ""
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
        got = self.headers.get("X-Empire-Token", got)
        q = urllib.parse.urlparse(self.path).query
        qs = urllib.parse.parse_qs(q)
        if "token" in qs:
            got = qs["token"][0]
        return got == expected and bool(got)

    def _serve_file(self, rel: str) -> None:
        path = (WWW / rel).resolve()
        if not str(path).startswith(str(WWW.resolve())) or not path.is_file():
            self.send_error(404)
            return
        ctype = "text/plain"
        if rel.endswith(".html"):
            ctype = "text/html; charset=utf-8"
        elif rel.endswith(".js"):
            ctype = "application/javascript"
        elif rel.endswith(".css"):
            ctype = "text/css"
        elif rel.endswith(".json"):
            ctype = "application/json"
        elif rel.endswith(".png"):
            ctype = "image/png"
        data = path.read_bytes()
        # rewrite API path + PWA install target for VPS mirror (HTTPS works off-LAN)
        if rel.endswith(".js"):
            data = data.replace(b'const API = "/cgi-bin/empire-api";', b'const API = "/home-ops/api";')
        if rel.endswith("manifest.json"):
            data = data.replace(
                b'"start_url": "./?source=pwa"',
                b'"start_url": "https://neverretire.ru/home-ops/?source=pwa"',
            )
            data = data.replace(b'"scope": "./"', b'"scope": "https://neverretire.ru/home-ops/"')
            data = data.replace(b'"name": "Empire Heal"', b'"name": "Empire Heal"')
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-Empire-Token, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/home-ops", "/home-ops/"):
            path = "/home-ops/index.html"
        if path.startswith("/home-ops/api"):
            if not self._token_ok():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            qs = urllib.parse.parse_qs(parsed.query)
            action = (qs.get("action") or ["status"])[0]
            svc = (qs.get("svc") or [""])[0]
            code, body = flint_api(action, load_token(), svc)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/home-ops/"):
            rel = path[len("/home-ops/") :] or "index.html"
            self._serve_file(rel)
            return
        # bare paths when proxied with strip
        if path == "/" or path == "/index.html":
            self._serve_file("index.html")
            return
        if path.lstrip("/") in (
            "app.js",
            "styles.css",
            "manifest.json",
            "sw.js",
            "icon-192.png",
            "icon-512.png",
        ):
            self._serve_file(path.lstrip("/"))
            return
        if path.startswith("/api"):
            if not self._token_ok():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            qs = urllib.parse.parse_qs(parsed.query)
            action = (qs.get("action") or ["status"])[0]
            svc = (qs.get("svc") or [""])[0]
            code, body = flint_api(action, load_token(), svc)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/home-ops/api") or path.startswith("/api"):
            if not self._token_ok():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode() if length else ""
            qs = urllib.parse.parse_qs(parsed.query)
            form = urllib.parse.parse_qs(body)
            action = (form.get("action") or qs.get("action") or ["status"])[0]
            svc = (form.get("svc") or qs.get("svc") or [""])[0]
            code, resp = flint_api(action, load_token(), svc)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
            return
        self.send_error(404)

    def _json(self, code: int, obj: dict) -> None:
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    httpd = ThreadingHTTPServer(LISTEN, Handler)
    print(f"home-ops listening on {LISTEN[0]}:{LISTEN[1]} token={bool(load_token())}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
