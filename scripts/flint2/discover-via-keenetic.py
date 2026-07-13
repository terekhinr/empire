#!/usr/bin/env python3
"""Найти GL.iNet Flint 2 в LAN через Keenetic RCI (potertiy.keenetic.pro)."""
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

FLINT_OUI = "94:83:c4"


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def auth(base: str, login: str, password: str) -> urllib.request.OpenerDirector:
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
        if err.code != 401:
            raise
        ch = err.headers.get("X-NDM-Challenge", "")
        realm = err.headers.get("X-NDM-Realm", "")
        md5 = hashlib.md5(f"{login}:{realm}:{password}".encode()).hexdigest()
        sha = hashlib.sha256(f"{ch}{md5}".encode()).hexdigest()
        body = json.dumps({"login": login, "password": sha}).encode()
        req = urllib.request.Request(
            f"{base}/auth",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener.open(req, timeout=20)
    return opener


def rci(opener, base: str, payload: object) -> object:
    req = urllib.request.Request(
        f"{base}/rci/",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def walk(obj, hits: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        mac = str(obj.get("mac", "")).lower()
        ip = str(obj.get("ip", obj.get("address", "")))
        name = str(obj.get("name", obj.get("hostname", "")))
        if FLINT_OUI in mac or "glinet" in name.lower() or "flint" in name.lower():
            hits.append((ip, mac or name))
        for v in obj.values():
            walk(v, hits)
    elif isinstance(obj, list):
        for item in obj:
            walk(item, hits)


def main() -> int:
    load_env()
    base = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    if not password:
        print("NO_PASSWORD", file=sys.stderr)
        return 2

    opener = auth(base, login, password)
    hits: list[tuple[str, str]] = []
    for q in (
        {"show": {"ip": {"hotspot": {}}}},
        {"show": {"associations": {}}},
        {"show": {"interface": {}}},
    ):
        try:
            walk(rci(opener, base, q), hits)
        except Exception as exc:
            print(f"WARN {q}: {exc}", file=sys.stderr)

    seen = set()
    for ip, meta in hits:
        if ip in seen:
            continue
        seen.add(ip)
        print(f"FLINT_CANDIDATE ip={ip} meta={meta}")
    if not seen:
        print("FLINT_NOT_ON_LAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
