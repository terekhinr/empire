#!/usr/bin/env python3
"""Static bootstrap + one-shot router SSH key registration for reverse tunnel."""
from __future__ import annotations

import json
import os
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = Path("/root/.xkeen-router-access.token")
AUTH_KEYS = Path("/root/.ssh/authorized_keys")
MARKER = "# keenetic-router-tunnel"
RESTART_COOLDOWN = Path("/tmp/xray-http-restart.ts")
RESTART_ALLOW = {"127.0.0.1", "::1"}
RESTART_PREFIXES = ("79.139.", "100.83.")  # MTS Moscow CGNAT (IP меняется)


def _restart_allowed(ip: str, token: str, expected: str) -> bool:
    if ip in RESTART_ALLOW:
        return True
    if any(ip.startswith(p) for p in RESTART_PREFIXES):
        return True
    return bool(expected and token == expected)
VPS_APPLY = ROOT / "vps-apply-xray-8443.sh"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _client_ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
        return self.client_address[0]

    def _restart_xray(self) -> bool:
        now = time.time()
        if RESTART_COOLDOWN.is_file():
            try:
                if now - float(RESTART_COOLDOWN.read_text().strip()) < 90:
                    return False
            except ValueError:
                pass
        subprocess.run([str(VPS_APPLY)], check=False, timeout=60)
        RESTART_COOLDOWN.write_text(str(now))
        return True

    def do_POST(self):
        if self.path == "/restart-xray":
            ip = self._client_ip()
            token = ""
            length = int(self.headers.get("Content-Length", 0))
            if length:
                body = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    token = str(json.loads(body).get("token", ""))
                except json.JSONDecodeError:
                    pass
            expected = TOKEN_FILE.read_text().strip() if TOKEN_FILE.is_file() else ""
            if not _restart_allowed(ip, token, expected):
                self.send_error(403, "forbidden")
                return
            restarted = self._restart_xray()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"ok": True, "restarted": restarted}).encode() + b"\n"
            )
            return
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
            f'restrict,port-forwarding,permitlisten="127.0.0.1:6222",'
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
        ip = self._client_ip()
        if any(ip.startswith(p) for p in RESTART_PREFIXES) or self.path.startswith("/register"):
            try:
                with open("/tmp/bootstrap-router-hits.log", "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {ip} {self.command} {self.path}\n")
            except OSError:
                pass
        if self.path.startswith("/register"):
            super().log_message(fmt, *args)


def main():
    host, port = "0.0.0.0", 8787
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"serving {ROOT} on {host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
