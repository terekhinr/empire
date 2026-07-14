#!/usr/bin/env python3
"""Временно сдвинуть Keenetic 192.168.1.1 → 192.168.1.254 (конфликт с Flint)."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

NEW_IP = os.environ.get("KEENETIC_NEW_IP", "192.168.1.254")


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


def main() -> int:
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    opener = auth(base, login, password)

    payload = {
        "interface": {
            "Bridge0": {
                "ip": {
                    "address": {
                        "address": NEW_IP,
                        "mask": "255.255.255.0",
                    }
                }
            }
        }
    }
    print("RCI move Bridge0 →", NEW_IP)
    res = rci(opener, base, payload)
    print(json.dumps(res, ensure_ascii=False)[:800])
    save = rci(opener, base, {"system": {"configuration": {"save": {}}}})
    print("save:", json.dumps(save, ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
