#!/usr/bin/env python3
"""Выполнить команду на Flint через Keenetic (dbclient/openssh)."""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

FLINT = "192.168.8.1"
PWD = os.environ.get("FLINT_ADMIN_PASSWORD", "_3ur6agan_")


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def keenetic_run(remote_cmd: str, wait: int = 60) -> str:
    load_env()
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    shell = (
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "export PATH=/opt/bin:/opt/sbin:/opt/usr/bin:$PATH; "
        + remote_cmd
    )
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        tn=telnetlib.Telnet("192.168.1.1", 23, timeout=25)
        tn.read_until(b"Login:", 15); tn.write({login!r}.encode()+b"\\n")
        tn.read_until(b"Password:", 15); tn.write({kpass!r}.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(3)
        tn.read_very_eager(); tn.write({shell!r}.encode()+b"\\r\\n"); time.sleep({wait})
        print(tn.read_very_eager().decode("utf-8","replace"))
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=wait + 90,
    )
    return p.stdout.decode()


def flint_exec(cmd: str, timeout: int = 120) -> str:
    """SSH to Flint using dbclient with password pipe."""
    escaped = cmd.replace("'", "'\\''")
    ssh_try = (
        f"( sleep 1; echo '{PWD}'; sleep 1 ) | "
        f"dbclient -y root@{FLINT} '{escaped}' 2>&1; "
        f"echo DBCLIENT_RC=$?"
    )
    out = keenetic_run(ssh_try, wait=timeout // 2)
    if "DBCLIENT_OK" in out or "DBCLIENT_RC=0" in out:
        return out
    # fallback openssh SSH_ASKPASS
    askpass = (
        f"printf '%s\\n' '#!/bin/sh' 'echo {PWD}' > /tmp/fap; chmod +x /tmp/fap; "
        f"DISPLAY=:0 SSH_ASKPASS=/tmp/fap SSH_ASKPASS_REQUIRE=force "
        f"/opt/bin/ssh -oNumberOfPasswordPrompts=1 -o PreferredAuthentications=password "
        f"-o PubkeyAuthentication=no -o StrictHostKeyChecking=no root@{FLINT} '{escaped}' 2>&1"
    )
    return keenetic_run(askpass, wait=timeout // 2)


def main() -> int:
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "uname -a; cat /etc/openwrt_release 2>/dev/null; echo DBCLIENT_OK"
    print(flint_exec(cmd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
