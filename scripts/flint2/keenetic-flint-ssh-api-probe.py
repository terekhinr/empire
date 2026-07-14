#!/usr/bin/env python3
"""Keenetic → Flint: SSH и GL.iNet API probe."""
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
        "printf 'GET / HTTP/1.0\\r\\nHost: 192.168.8.1\\r\\n\\r\\n' | nc 192.168.8.1 22 | head -3; "
        "printf 'GET /api/router/status HTTP/1.0\\r\\nHost: 192.168.8.1\\r\\n\\r\\n' | nc 192.168.8.1 80 | head -20; "
        "which ssh dropbear sshpass 2>/dev/null; "
        "ssh -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=no root@192.168.8.1 echo_ok 2>&1 | head -3"
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
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(12)
        print(tn.read_very_eager().decode("utf-8","replace")[-4000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=60,
    )
    print(p.stdout.decode())
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
