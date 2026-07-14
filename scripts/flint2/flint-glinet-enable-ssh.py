#!/usr/bin/env python3
"""Один проход: challenge → login → enable SSH на Flint через Keenetic."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

HOST = "192.168.8.1"
USERS = ["root", "admin"]
PASSWORDS = ["_3ur6agan_", "3ur6agan", "5RD3XCZ6WN", "goodlife"]


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def nc_cmd(body: dict) -> str:
    payload = json.dumps(body, separators=(",", ":"))
    n = len(payload.encode())
    http = (
        f"POST /rpc HTTP/1.0\\r\\nHost: {HOST}\\r\\n"
        f"Content-Type: application/json\\r\\nglinet: 1\\r\\n"
        f"Content-Length: {n}\\r\\n\\r\\n{payload}"
    )
    return (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        f"printf {json.dumps(http)} | nc {HOST} 80; echo"
    )


def keenetic_run(shell_cmd: str, wait: int = 8) -> str:
    load_env()
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        tn=telnetlib.Telnet("192.168.1.1", 23, timeout=20)
        tn.read_until(b"Login:", 12); tn.write({login!r}.encode()+b"\\n")
        tn.read_until(b"Password:", 12); tn.write({kpass!r}.encode()+b"\\n"); time.sleep(1.5)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(2.5)
        tn.read_very_eager(); tn.write({shell_cmd!r}.encode()+b"\\r\\n"); time.sleep({wait})
        out=tn.read_very_eager().decode("utf-8","replace")
        print(out[-5000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=60,
    )
    return p.stdout.decode()


def parse_json(raw: str) -> dict | None:
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("{") and "jsonrpc" in s:
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
    m = re.search(r"\{.*\"jsonrpc\".*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def crypt_password(password: str, alg: int, salt: str) -> str:
    import crypt

    return crypt.crypt(password, f"${alg}${salt}$")


def rpc(body: dict) -> dict:
    raw = keenetic_run(nc_cmd(body), wait=8)
    j = parse_json(raw)
    if not j:
        raise RuntimeError(f"no json in: {raw[-800:]}")
    return j


def try_login(user: str, password: str) -> str | None:
    ch = rpc({"jsonrpc": "2.0", "method": "challenge", "params": {"username": user}, "id": 0})
    if "error" in ch:
        return None
    r = ch["result"]
    cipher = crypt_password(password, int(r["alg"]), r["salt"])
    digest = hashlib.md5(f"{user}:{cipher}:{r['nonce']}".encode()).hexdigest()
    lg = rpc({"jsonrpc": "2.0", "method": "login", "params": {"username": user, "hash": digest}, "id": 1})
    if "error" in lg:
        return None
    return lg["result"]["sid"]


def main() -> int:
    sid = None
    cred = None
    env_pwd = os.environ.get("FLINT_ADMIN_PASSWORD", "")
    passwords = ([env_pwd] if env_pwd else []) + [p for p in PASSWORDS if p != env_pwd]
    for user in USERS:
        for pwd in passwords:
            print(f"try {user} / {pwd!r}...")
            sid = try_login(user, pwd)
            if sid:
                cred = (user, pwd)
                break
        if sid:
            break
    if not sid:
        print("LOGIN FAILED — проверьте пароль в админке")
        return 1
    print(f"login ok: {cred[0]} sid={sid[:12]}...")

    print("enable ssh...")
    for fn, args in [
        ("set_dropbear", {"enable": True, "port": 22, "password_auth": True, "root_password_auth": True}),
        ("set_dropbear_config", {"enable": True}),
    ]:
        res = rpc({"jsonrpc": "2.0", "method": "call", "params": [sid, "system", fn, args], "id": 2})
        print(fn, json.dumps(res)[:200])

    print("ssh probe...")
    raw = keenetic_run(
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "printf '' | nc 192.168.8.1 22 | head -1 || echo CLOSED",
        wait=5,
    )
    print(raw[-400:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
