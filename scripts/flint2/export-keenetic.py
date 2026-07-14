#!/usr/bin/env python3
"""Экспорт настроек Keenetic для миграции на Flint."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

OUT = Path("/root/projects/empire/scripts/flint2/keenetic-export.json")

QUERIES = [
    {"show": {"version": {}}},
    {"show": {"sc": {"ip": {"name-server": {}, "hotspot": {}, "dhcp": {}, "route": {}}}}},
    {"show": {"sc": {"interface": {}}}},
    {"show": {"sc": {"system": {}}}},
    {"show": {"ip": {"hotspot": {}}}},
    {"show": {"associations": {}}},
    {"show": {"cloud": {}}},
    {"show": {"rc": {"ndns": {}}}},
    {"show": {"rc": {"ip": {"static": {}}}}},
    {"show": {"sc": {"usb": {}}}},
    {"show": {"sc": {"apps": {}}}},
    {"show": {"interface": {}}},
    {"show": {"rc": {"wireguard": {}}}},
    {"show": {"rc": {"openvpn": {}}}},
    {"show": {"components": {"transmission": {}}}},
    {"show": {"components": {"storage": {}}}},
]


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
    with opener.open(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    opener = auth(base, login, password)
    export = {}
    for q in QUERIES:
        key = json.dumps(q, sort_keys=True)
        try:
            export[key] = rci(opener, base, q)
        except Exception as exc:
            export[key] = {"error": str(exc)}
    OUT.write_text(json.dumps(export, ensure_ascii=False, indent=2))
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
