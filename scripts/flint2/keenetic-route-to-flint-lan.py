#!/usr/bin/env python3
"""Добавить маршрут 192.168.8.0/24 через Flint WAN и проверить доступ к 192.168.8.1."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

FLINT_GW = "192.168.1.99"
FLINT_LAN = "192.168.8.1"
NET = "192.168.8.0/24"


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def auth(base, login, password):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    jar = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=ctx),
    )
    try:
        opener.open(urllib.request.Request(f"{base}/auth"), timeout=20)
    except urllib.error.HTTPError as err:
        ch = err.headers.get("X-NDM-Challenge", "")
        realm = err.headers.get("X-NDM-Realm", "")
        md5 = hashlib.md5(f"{login}:{realm}:{password}".encode()).hexdigest()
        sha = hashlib.sha256(f"{ch}{md5}".encode()).hexdigest()
        opener.open(
            urllib.request.Request(
                f"{base}/auth",
                data=json.dumps({"login": login, "password": sha}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=20,
        )
    return opener


def rci(opener, base, payload):
    req = urllib.request.Request(
        f"{base}/rci/",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        raw = resp.read().decode()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def main() -> int:
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")

    opener = auth(base, login, password)

    payloads = [
        {
            "ip": {
                "route": {
                    "network": "192.168.8.0",
                    "mask": "255.255.255.0",
                    "gateway": FLINT_GW,
                    "interface": "Bridge0",
                    "auto": True,
                    "comment": "flint2-lan",
                }
            }
        },
    ]
    for p in payloads:
        try:
            out = rci(opener, base, p)
            print("RCI", json.dumps(p), "=>", str(out)[:300])
        except Exception as exc:
            print("RCI fail", p, exc)

    rci(opener, base, {"system": {"configuration": {"save": {}}}})

    # probe from HA via tailscale
    ha = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "root@100.80.133.85",
            f"curl -sI -m5 http://{FLINT_LAN}/ 2>&1 | head -5; ping -c1 -W2 {FLINT_LAN} 2>&1 | tail -2",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print("HA probe:", ha.stdout or ha.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
