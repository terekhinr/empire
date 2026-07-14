#!/usr/bin/env python3
"""Попытка GL.iNet API login и включение SSH на Flint."""
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


def try_login(pwd: str, klogin: str, kpass: str) -> None:
    body = json.dumps({"username": "admin", "password": pwd})
    req = (
        "POST /api/router/login HTTP/1.0\\r\\n"
        "Host: 192.168.8.1\\r\\n"
        "Content-Type: application/json\\r\\n"
        f"Content-Length: {len(body)}\\r\\n\\r\\n"
        f"{body}"
    )
    cmd = (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        f"printf {req!r} | nc 192.168.8.1 80"
    )
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        tn=telnetlib.Telnet("192.168.1.1",23,timeout=25)
        tn.read_until(b"Login:",15); tn.write({klogin!r}.encode()+b"\\n")
        tn.read_until(b"Password:",15); tn.write({kpass!r}.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(4)
        tn.read_very_eager(); tn.write({cmd!r}.encode()+b"\\r\\n"); time.sleep(8)
        print("=== pwd try ===")
        print(tn.read_very_eager().decode("utf-8","replace")[-3000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        timeout=60,
    )


def main() -> None:
    load_env()
    klogin = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    # из экспорта Keenetic (Wi‑Fi); часто совпадает с admin
    for pwd in ("p0tertiy", "goodlife", "admin", ""):
        print(f"Trying admin password len={len(pwd)}")
        try_login(pwd, klogin, kpass)


if __name__ == "__main__":
    main()
