#!/usr/bin/env python3
"""Keenetic RCI auth + heal via admin API (no SSH :222)."""
from __future__ import annotations

import os
import hashlib
import json
import ssl
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = os.environ.get("KEENETIC_RCI_URL", "https://potertiy.keenetic.pro")
LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
PC_MAC = "94:de:80:64:ed:e6"
SALUT_MAC = "04:05:dd:c5:eb:a4"
HEAL_URL = "http://193.233.232.48:8787/55-minimal-nfqws2.sh"


def auth_session() -> urllib.request.OpenerDirector:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    jar = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=ctx),
    )
    req = urllib.request.Request(f"{BASE}/auth", method="GET")
    try:
        with opener.open(req, timeout=20) as resp:
            if resp.status == 200:
                return opener
            challenge = resp.headers.get("X-NDM-Challenge", "")
            realm = resp.headers.get("X-NDM-Realm", "")
    except urllib.error.HTTPError as err:
        if err.code != 401:
            raise
        challenge = err.headers.get("X-NDM-Challenge", "")
        realm = err.headers.get("X-NDM-Realm", "")
    if not challenge or not realm:
        raise RuntimeError("no challenge/realm from /auth")
    md5 = hashlib.md5(f"{LOGIN}:{realm}:{PASSWORD}".encode()).hexdigest()
    sha = hashlib.sha256(f"{challenge}{md5}".encode()).hexdigest()
    body = json.dumps({"login": LOGIN, "password": sha}).encode()
    req = urllib.request.Request(
        f"{BASE}/auth",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"auth post {resp.status}: {resp.read()[:200]}")
    return opener


def rci_post(opener: urllib.request.OpenerDirector, payload) -> object:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/rci/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def load_env_file() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def set_host_policy(opener, mac: str, policy: str | None) -> object:
    if policy is None or policy == "conform":
        payload = {"ip": {"hotspot": {"host": {"mac": mac, "conform": {}}}}}
    else:
        payload = {"ip": {"hotspot": {"host": {"mac": mac, "policy": policy}}}}
    return rci_post(opener, payload)


def main() -> int:
    load_env_file()
    global BASE, LOGIN, PASSWORD
    BASE = os.environ.get("KEENETIC_RCI_URL", BASE)
    LOGIN = os.environ.get("KEENETIC_ADMIN_LOGIN", LOGIN)
    PASSWORD = os.environ.get("KEENETIC_ADMIN_PASSWORD", PASSWORD)
    if not PASSWORD:
        print("Set KEENETIC_ADMIN_PASSWORD", file=sys.stderr)
        return 2
    reboot = "--reboot" in sys.argv
    policy = "conform"
    for arg in sys.argv[1:]:
        if arg.startswith("--policy="):
            policy = arg.split("=", 1)[1]
    print("=== Keenetic RCI heal ===")
    opener = auth_session()
    print("AUTH OK")

    ver = rci_post(opener, {"show": {"version": {}}})
    print("version:", str(ver)[:200])

    for mac in (PC_MAC, SALUT_MAC):
        out = set_host_policy(opener, mac, policy)
        print(f"policy {policy} {mac}:", str(out)[:120])

    save = rci_post(opener, {"system": {"configuration": {"save": {}}}})
    print("save:", str(save)[:120])

    if reboot:
        reboot_out = rci_post(opener, {"system": {"reboot": {}}})
        print("reboot:", str(reboot_out)[:120])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise
