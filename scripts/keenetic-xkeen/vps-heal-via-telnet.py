#!/usr/bin/env python3
"""Keenetic: enable telnet + heal Entware via CLI (admin RCI)."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
HEAL = "export PATH=/opt/bin:/opt/sbin:$PATH; curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh"


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def auth_opener() -> urllib.request.OpenerDirector:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar()),
        urllib.request.HTTPSHandler(context=ctx),
    )
    req = urllib.request.Request(f"{BASE}/auth", method="GET")
    try:
        op.open(req, timeout=20)
    except urllib.error.HTTPError as err:
        if err.code != 401:
            raise
        ch, re = err.headers.get("X-NDM-Challenge", ""), err.headers.get("X-NDM-Realm", "")
    else:
        return op
    md5 = hashlib.md5(f"{LOGIN}:{re}:{PASSWORD}".encode()).hexdigest()
    sha = hashlib.sha256(f"{ch}{md5}".encode()).hexdigest()
    op.open(
        urllib.request.Request(
            f"{BASE}/auth",
            data=json.dumps({"login": LOGIN, "password": sha}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
        timeout=20,
    )
    return op


def rci(op: urllib.request.OpenerDirector, payload: object) -> object:
    req = urllib.request.Request(
        f"{BASE}/rci/",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with op.open(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def telnet_heal(host: str, port: int = 23) -> bool:
  # Keenetic CLI: login admin, exec sh, run heal
    try:
        import telnetlib
    except ImportError:
        print("no telnetlib")
        return False
    tn = telnetlib.Telnet(host, port, timeout=20)
    tn.read_until(b"Login:", timeout=15)
    tn.write(LOGIN.encode("ascii") + b"\n")
    tn.read_until(b"Password:", timeout=15)
    tn.write(PASSWORD.encode("ascii") + b"\n")
    time.sleep(1)
    out = tn.read_very_eager().decode("utf-8", errors="replace")
    if "failed" in out.lower() or "denied" in out.lower():
        print("telnet auth fail:", out[:200])
        tn.close()
        return False
    tn.write(b"exec sh\n")
    time.sleep(2)
    tn.write(HEAL.encode("utf-8") + b"\n")
    time.sleep(25)
    result = tn.read_very_eager().decode("utf-8", errors="replace")
    tn.write(b"exit\n")
    tn.close()
    print(result[-1500:])
    return "youtube=200" in result or "NFQUEUE=" in result


def main() -> int:
    load_env()
    global PASSWORD, LOGIN, BASE
    PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", PASSWORD)
    LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", LOGIN)
    BASE = os.environ.get("KEENETIC_RCI_URL", BASE)
    if not PASSWORD:
        print("NO_PASSWORD", file=sys.stderr)
        return 2

    op = auth_opener()
    print("AUTH OK")

    # enable telnet LAN + try WAN
    for payload in (
        {"ip": {"telnet": {"port": 23}}},
        {"service": {"telnet": {}}},
        {"components": {"telnet": {"enable": True}}},
    ):
        try:
            out = rci(op, payload)
            print("rci", payload, "->", str(out)[:200])
        except Exception as exc:
            print("rci err", payload, exc)

    rci(op, {"system": {"configuration": {"save": {}}}})

    host = BASE.replace("https://", "").replace("http://", "").split("/")[0]
    for target in (host, "potertiy.keenetic.pro", "192.168.1.1"):
        print(f"telnet try {target}:23")
        if telnet_heal(target):
            print("HEAL OK via", target)
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
