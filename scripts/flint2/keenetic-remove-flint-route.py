#!/usr/bin/env python3
"""Удалить static route flint2-lan на Keenetic."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path


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
        return json.loads(resp.read().decode())


def main() -> None:
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    opener = auth(base, login, password)
    routes = rci(opener, base, {"show": {"sc": {"ip": {"route": {}}}}})
    print("BEFORE", json.dumps(routes, ensure_ascii=False)[:3000])
    out = rci(
        opener,
        base,
        {
            "ip": {
                "route": {
                    "network": "192.168.8.0",
                    "mask": "255.255.255.0",
                    "gateway": "192.168.1.99",
                    "interface": "Bridge0",
                    "comment": "flint2-lan",
                    "delete": True,
                }
            }
        },
    )
    print("DELETE", json.dumps(out, ensure_ascii=False))
    rci(opener, base, {"system": {"configuration": {"save": {}}}})


if __name__ == "__main__":
    main()
