#!/usr/bin/env python3
"""SNAT на Keenetic: трафик к 192.168.8.0/24 с маской 192.168.8.254."""
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
        "iptables -t nat -C POSTROUTING -d 192.168.8.0/24 -j SNAT --to-source 192.168.8.254 2>/dev/null || "
        "iptables -t nat -A POSTROUTING -d 192.168.8.0/24 -j SNAT --to-source 192.168.8.254; "
        "echo SNAT_OK"
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
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(8)
        print(tn.read_very_eager().decode("utf-8","replace")[-2000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=45,
    )
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85",
         "ping -c1 -W2 192.168.8.1; curl -sI -m8 http://192.168.8.1/ | head -10"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(p.stdout)
    print(p.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
