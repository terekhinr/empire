#!/usr/bin/env python3
"""Вход в Flint через Keenetic: init/login/enable-ssh (nc HTTP)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

HOST = "192.168.8.1"
USER = "root"
PASSWORDS = ["_3ur6agan_", "5RD3XCZ6WN", "goodlife", "p0tertiy", "admin", ""]


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def nc_post_json(body: dict) -> str:
    """Build shell command: POST JSON to Flint /rpc via nc."""
    payload = json.dumps(body, separators=(",", ":"))
    n = len(payload.encode())
    http = (
        f"POST /rpc HTTP/1.0\\r\\n"
        f"Host: {HOST}\\r\\n"
        f"Content-Type: application/json\\r\\n"
        f"glinet: 1\\r\\n"
        f"Content-Length: {n}\\r\\n\\r\\n"
        f"{payload}"
    )
    return (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        f"printf {json.dumps(http)} | nc {HOST} 80"
    )


def keenetic_exec(shell_cmd: str, wait: int = 10) -> str:
    load_env()
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        H="192.168.1.1"; L={login!r}; P={kpass!r}
        cmd={shell_cmd!r}
        tn=telnetlib.Telnet(H,23,timeout=25)
        tn.read_until(b"Login:",15); tn.write(L.encode()+b"\\n")
        tn.read_until(b"Password:",15); tn.write(P.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(4)
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep({wait})
        print(tn.read_very_eager().decode("utf-8","replace"))
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=120,
    )
    return p.stdout.decode()


def parse_json_response(raw: str) -> dict | None:
    # strip HTTP headers, find json body
    m = re.search(r"\{[^{}]*\"jsonrpc\".*\}", raw, re.DOTALL)
    if not m:
        # multiline json
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("{") and "jsonrpc" in s:
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    pass
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def rpc(body: dict, wait: int = 10) -> dict:
    raw = keenetic_exec(nc_post_json(body), wait)
    j = parse_json_response(raw)
    return j or {"_raw": raw[-2500:]}


def crypt_password(password: str, alg: int, salt: str) -> str:
    import crypt

    return crypt.crypt(password, f"${alg}${salt}$")


def try_login(password: str) -> str | None:
    ch = rpc({"jsonrpc": "2.0", "method": "challenge", "params": {"username": USER}, "id": 0})
    if not ch or "result" not in ch:
        return None
    r = ch["result"]
    cipher = crypt_password(password, int(r["alg"]), r["salt"])
    digest = hashlib.md5(f"{USER}:{cipher}:{r['nonce']}".encode()).hexdigest()
    lg = rpc({"jsonrpc": "2.0", "method": "login", "params": {"username": USER, "hash": digest}, "id": 1})
    if not lg or "error" in lg:
        return None
    return lg.get("result", {}).get("sid")


def gl_call(sid: str, module: str, func: str, args=None) -> dict:
    params = [sid, module, func]
    if args is not None:
        params.append(args)
    return rpc({"jsonrpc": "2.0", "method": "call", "params": params, "id": 2}, wait=12)


def main() -> int:
    print("=== ping ===")
    print(keenetic_exec("ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; ping -c1 -W2 192.168.8.1", 6)[-400:])

    print("=== check_initialized ===")
    init = rpc({"jsonrpc": "2.0", "method": "call", "params": ["", "ui", "check_initialized"], "id": 1})
    print(json.dumps(init, ensure_ascii=False)[:600])

    initialized = True
    if init and "result" in init:
        res = init["result"]
        if isinstance(res, list) and res:
            initialized = bool(res[0].get("initialized", True))
        elif isinstance(res, dict):
            initialized = bool(res.get("initialized", True))

    sid = None
    if not initialized:
        print("=== ui init ===")
        for pwd in ("5RD3XCZ6WN", "p0tertiy", "goodlife"):
            r = rpc(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": ["", "ui", "init", {"lang": "en", "username": "root", "password": pwd, "security_rule": 0}],
                    "id": 3,
                },
                wait=15,
            )
            print(f"init {pwd}: {json.dumps(r, ensure_ascii=False)[:300]}")
            sid = try_login(pwd)
            if sid:
                print(f"login after init OK")
                break

    if not sid:
        for pwd in PASSWORDS:
            print(f"try login: {pwd!r}")
            sid = try_login(pwd)
            if sid:
                print(f"login OK")
                break

    if not sid:
        print("LOGIN FAILED")
        return 1

    print("=== enable SSH ===")
    for fn, args in [
        ("set_dropbear", {"enable": True, "port": 22, "password_auth": True, "root_password_auth": True}),
        ("set_dropbear_config", {"enable": True}),
    ]:
        r = gl_call(sid, "system", fn, args)
        print(f"{fn}: {json.dumps(r, ensure_ascii=False)[:400]}")

    print("=== SSH probe ===")
    print(keenetic_exec(
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "printf '' | nc -w3 192.168.8.1 22 | head -1 || echo CLOSED",
        6,
    )[-400:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
