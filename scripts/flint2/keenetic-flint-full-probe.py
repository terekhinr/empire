#!/usr/bin/env python3
"""Keenetic: alias + SNAT + nc HTTP к Flint одной сессией."""
from __future__ import annotations

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
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    cmd = (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "ping -c2 -W2 192.168.8.1; "
        "timeout 8 sh -c \"printf 'GET / HTTP/1.0\\r\\nHost: 192.168.8.1\\r\\n\\r\\n' | nc 192.168.8.1 80\" | head -20"
    )
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        H="192.168.1.1"; L={login!r}; P={password!r}
        cmd={cmd!r}
        tn=telnetlib.Telnet(H,23,timeout=25)
        tn.read_until(b"Login:",15); tn.write(L.encode()+b"\\n")
        tn.read_until(b"Password:",15); tn.write(P.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(4)
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(20)
        print(tn.read_very_eager().decode("utf-8","replace")[-3000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=90,
    )
    print(p.stdout.decode())
    print(p.stderr.decode())
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
