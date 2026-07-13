#!/usr/bin/env python3
"""Детали хоста Flint2 в Keenetic hotspot."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

TARGET_MAC = "94:83:c4:df:8a:b2"


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
        body = json.dumps({"login": login, "password": sha}).encode()
        opener.open(
            urllib.request.Request(
                f"{base}/auth",
                data=body,
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


def find_mac(obj, mac):
    mac = mac.lower()
    if isinstance(obj, dict):
        if str(obj.get("mac", "")).lower() == mac:
            return obj
        for v in obj.values():
            hit = find_mac(v, mac)
            if hit:
                return hit
    elif isinstance(obj, list):
        for item in obj:
            hit = find_mac(item, mac)
            if hit:
                return hit
    return None


def main():
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    opener = auth(base, login, password)
    data = rci(opener, base, {"show": {"ip": {"hotspot": {}}}})
    host = find_mac(data, TARGET_MAC)
    print(json.dumps(host or {"error": "not found"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
