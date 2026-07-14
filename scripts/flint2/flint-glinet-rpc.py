#!/usr/bin/env python3
"""GL.iNet JSON-RPC: login, enable SSH, run bootstrap via Keenetic hop."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

HOST = os.environ.get("FLINT_HOST", "192.168.8.1")
PASSWORD = os.environ.get("FLINT_ADMIN_PASSWORD", "")
USERNAME = os.environ.get("FLINT_ADMIN_USER", "root")


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def crypt_password(password: str, alg: int, salt: str) -> str:
    import crypt

    return crypt.crypt(password, f"${alg}${salt}$")


def rpc_via_keenetic(payload: dict) -> str:
    """Run curl to Flint from Keenetic shell (192.168.8.254 alias)."""
    load_env()
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    body = json.dumps(payload, separators=(",", ":"))
    cmd = (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        f"printf %s {json.dumps(body)} | "
        f"curl -sS -H 'Content-Type: application/json' -H 'glinet: 1' "
        f"-d @- http://{HOST}/rpc"
    )
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        H="192.168.1.1"; L={login!r}; P={kpass!r}
        cmd={cmd!r}
        tn=telnetlib.Telnet(H,23,timeout=25)
        tn.read_until(b"Login:",15); tn.write(L.encode()+b"\\n")
        tn.read_until(b"Password:",15); tn.write(P.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(4)
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(10)
        print(tn.read_very_eager().decode("utf-8","replace")[-6000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=90,
    )
    out = p.stdout.decode()
    # curl output is after last ~ # prompt noise
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and "jsonrpc" in line:
            return line
    return out


def call_rpc(payload: dict) -> dict:
    raw = rpc_via_keenetic(payload)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"bad rpc response: {raw[:500]}")


def login(password: str) -> str:
    ch = call_rpc({"jsonrpc": "2.0", "method": "challenge", "params": {"username": USERNAME}, "id": 0})
    if "error" in ch:
        raise RuntimeError(f"challenge failed: {ch}")
    r = ch["result"]
    cipher = crypt_password(password, int(r["alg"]), r["salt"])
    digest = hashlib.md5(f"{USERNAME}:{cipher}:{r['nonce']}".encode()).hexdigest()
    lg = call_rpc(
        {
            "jsonrpc": "2.0",
            "method": "login",
            "params": {"username": USERNAME, "hash": digest},
            "id": 1,
        }
    )
    if "error" in lg:
        raise RuntimeError(f"login failed: {lg}")
    return lg["result"]["sid"]


def gl_call(sid: str, module: str, func: str, args: list | dict | None = None) -> dict:
    params: list = [sid, module, func]
    if args is not None:
        params.append(args)
    return call_rpc({"jsonrpc": "2.0", "method": "call", "params": params, "id": 2})


def main() -> int:
    if not PASSWORD:
        print("FLINT_ADMIN_PASSWORD не задан", file=sys.stderr)
        print("Пример: FLINT_ADMIN_PASSWORD='...' python3 flint-glinet-rpc.py status", file=sys.stderr)
        return 2

    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    sid = login(PASSWORD)
    print(f"login ok sid={sid[:8]}...")

    if action == "status":
        print(json.dumps(gl_call(sid, "system", "get_status"), indent=2, ensure_ascii=False))
        return 0

    if action == "enable-ssh":
        # GL.iNet 4.x: dropbear via system/set_dropbear
        for mod, fn, args in [
            ("system", "set_dropbear", {"enable": True, "port": 22, "password_auth": True, "root_password_auth": True}),
            ("system", "set_dropbear_config", {"enable": True}),
        ]:
            try:
                res = gl_call(sid, mod, fn, args)
                print(f"{mod}.{fn}: {res}")
            except Exception as e:
                print(f"{mod}.{fn}: {e}")
        return 0

    if action == "bootstrap":
        cmd = "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
        res = gl_call(sid, "system", "exec", {"command": cmd})
        print(res)
        return 0

    print(f"unknown action: {action}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
