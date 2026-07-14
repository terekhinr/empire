#!/usr/bin/env python3
"""Probe GL.iNet /rpc без пароля через Keenetic."""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
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


def main() -> int:
    load_env()
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    payloads = [
        {"jsonrpc": "2.0", "method": "challenge", "params": {"username": "root"}, "id": 0},
        {"jsonrpc": "2.0", "method": "call", "params": ["", "ui", "check_initialized"], "id": 1},
    ]
    for pl in payloads:
        body = json.dumps(pl)
        cmd = (
            "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
            f"printf %s {json.dumps(body)} | "
            "curl -sS -H 'Content-Type: application/json' -H 'glinet: 1' "
            "-d @- http://192.168.8.1/rpc; echo"
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
            tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(8)
            print("===", {pl.get("method")!r}, "===")
            print(tn.read_very_eager().decode("utf-8","replace")[-3000:])
            tn.write(b"exit\\r\\n"); tn.close()
            '''
        ).strip()
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "root@100.80.133.85", "python3 -"],
            input=script.encode(),
            timeout=60,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
