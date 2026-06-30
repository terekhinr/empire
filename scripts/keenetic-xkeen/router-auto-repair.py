#!/usr/bin/env python3
"""Keenetic auto-repair: RCI diagnostics + OPKG/SSH fix + telnet heal."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
HEAL_URL = os.environ.get(
    "KEENETIC_HEAL_URL",
    "http://193.233.232.48:8787/54-emergency-restore.sh",
)
DOWNGRADE_URL = os.environ.get(
    "KEENETIC_NFQWS2_DOWNGRADE",
    "https://github.com/nfqws/nfqws2-keenetic/releases/download/v1.1.5/nfqws2-keenetic_1.1.5_mipsel-3.4.ipk",
)


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
    with op.open(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def rci_get(op: urllib.request.OpenerDirector, path: str) -> object:
    req = urllib.request.Request(f"{BASE}/rci/{path}", method="GET")
    with op.open(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def poll_bg(op: urllib.request.OpenerDirector, path: str, timeout: int = 120) -> object:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = rci_get(op, path)
        except Exception as exc:
            print(f"poll {path} err: {exc}")
            time.sleep(3)
            continue
        if isinstance(last, dict) and last.get("continued"):
            time.sleep(3)
            continue
        return last
    return last


def telnet_cmd(host: str, cmd: str, *, shell: bool = True) -> str:
    import telnetlib

    tn = telnetlib.Telnet(host, 23, timeout=25)
    tn.read_until(b"Login:", timeout=15)
    tn.write(LOGIN.encode("ascii") + b"\n")
    tn.read_until(b"Password:", timeout=15)
    tn.write(PASSWORD.encode("ascii") + b"\n")
    time.sleep(1.5)
    boot = tn.read_very_eager().decode("utf-8", errors="replace")
    if "failed" in boot.lower() or "denied" in boot.lower():
        tn.close()
        return f"AUTH_FAIL {boot[:200]}"
    if shell:
        tn.write(b"exec sh\r\n")
        time.sleep(4)
        chunk = tn.read_very_eager().decode("utf-8", errors="replace")
        if "system failed" in chunk.lower():
            tn.close()
            return f"EXEC_SH_FAIL {chunk[-400:]}"
    tn.write(cmd.encode("utf-8") + b"\r\n")
    time.sleep(30 if "curl" in cmd else 8)
    out = tn.read_very_eager().decode("utf-8", errors="replace")
    tn.write(b"exit\r\n")
    tn.close()
    return out[-5000:]


def main() -> int:
    load_env()
    global BASE, LOGIN, PASSWORD
    BASE = os.environ.get("KEENETIC_RCI_URL", BASE)
    LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", LOGIN)
    PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", PASSWORD)
    if not PASSWORD:
        print("NO_PASSWORD")
        return 2

    op = auth_opener()
    print("AUTH OK")

    for q in (
        {"show": {"version": {}}},
        {"show": {"system": {}}},
        {"show": {"media": {}}},
        {"show": {"rc": {"ssh": {}}}},
        {"show": {"rc": {"components": {}}}},
    ):
        try:
            out = rci(op, q)
            print(f"\n=== {q} ===")
            print(json.dumps(out, ensure_ascii=False)[:2500])
        except Exception as exc:
            print(f"ERR {q}: {exc}")

    print("\n=== Reset PC/Salut policies ===")
    for mac in ("94:de:80:64:ed:e6", "04:05:dd:c5:eb:a4"):
        try:
            out = rci(op, {"ip": {"hotspot": {"host": {"mac": mac, "conform": {}}}}})
            print(mac, str(out)[:120])
        except Exception as exc:
            print(mac, "ERR", exc)

    print("\n=== Try reinstall OPKG component ===")
    for payload in (
        {"components": {"install": {"opkg": {}}}},
        {"components": {"install": {"ssh": {}}}},
    ):
        try:
            out = rci(op, payload)
            print("start", payload, "->", str(out)[:200])
            if isinstance(out, dict) and out.get("continued"):
                path = "components/install"
                final = poll_bg(op, path, 180)
                print("final", path, "->", str(final)[:500])
        except Exception as exc:
            print("ERR", payload, exc)

    print("\n=== Enable SSH port 222 ===")
    for payload in (
        {"ip": {"ssh": {"port": 222}}},
        {"ssh": {"port": 222, "security-level": "public"}},
        {"components": {"ssh": {"enable": True}}},
    ):
        try:
            out = rci(op, payload)
            print(payload, "->", str(out)[:200])
        except Exception as exc:
            print("ERR", payload, exc)

    rci(op, {"system": {"configuration": {"save": {}}}})
    print("config saved")

    host = "192.168.1.1"
    print(f"\n=== Telnet heal via armbian path {host} ===")
    heal_cmd = (
        f"export PATH=/opt/bin:/opt/sbin:$PATH; "
        f"wget -q -O /opt/tmp/nfqws2-downgrade.ipk '{DOWNGRADE_URL}' || "
        f"curl -fsSL -o /opt/tmp/nfqws2-downgrade.ipk '{DOWNGRADE_URL}'; "
        f"opkg install --force-downgrade --force-reinstall /opt/tmp/nfqws2-downgrade.ipk 2>/dev/null || true; "
        f"curl -fsSL {HEAL_URL} | sh"
    )
    # run telnet from local if reachable, else instruct
    try:
        out = telnet_cmd(host, heal_cmd, shell=True)
        print(out)
        if "youtube=200" in out or "-> 200" in out:
            print("HEAL_OK")
            return 0
        if "EXEC_SH_FAIL" in out:
            print("EXEC_SH_STILL_BROKEN")
    except Exception as exc:
        print("telnet local fail:", exc)

    print("\n=== Try telnet without shell (ndmc only) ===")
    try:
        out = telnet_cmd(host, "show version", shell=False)
        print(out[-1500:])
    except Exception as exc:
        print("telnet ndmc fail:", exc)

    print("\nDONE partial - check output above")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
