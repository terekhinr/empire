#!/usr/bin/env python3
"""SSH на Flint с Keenetic shell (openssh + SSH_ASKPASS)."""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

FLINT_PWD = os.environ.get("FLINT_ADMIN_PASSWORD", "_3ur6agan_")


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
    remote_cmd = (
        "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
    )
    cmd = (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "export PATH=/opt/bin:/opt/sbin:$PATH; "
        "opkg install openssh-client 2>&1 | tail -3; "
        f"printf '%s\\n' '#!/bin/sh' 'echo {FLINT_PWD}' > /tmp/flint_askpass; "
        "chmod +x /tmp/flint_askpass; "
        "DISPLAY=:0 SSH_ASKPASS=/tmp/flint_askpass SSH_ASKPASS_REQUIRE=force "
        "/opt/bin/ssh -oNumberOfPasswordPrompts=1 -o PreferredAuthentications=password "
        "-o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=12 "
        f"root@192.168.8.1 {remote_cmd!r} 2>&1 | tail -30"
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
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(120)
        print(tn.read_very_eager().decode("utf-8","replace")[-8000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=180,
    )
    print(p.stdout.decode())
    if p.stderr:
        print(p.stderr.decode()[-500:])
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
