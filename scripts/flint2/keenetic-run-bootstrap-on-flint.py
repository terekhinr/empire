#!/usr/bin/env python3
"""Keenetic telnet: curl bootstrap на Flint с alias IP 192.168.8.254."""
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
        "wget -qO- -T10 http://192.168.8.1/ 2>&1 | head -8; "
        "wget -qO- -T10 http://192.168.8.1/cgi-bin/luci/ 2>&1 | head -5; "
        "nc -z -w3 192.168.8.1 22 && echo SSH_OPEN || echo SSH_CLOSED"
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
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(180)
        print(tn.read_very_eager().decode("utf-8","replace")[-8000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=240,
    )
    print(p.stdout.decode())
    if p.stderr:
        print(p.stderr.decode())
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
