#!/usr/bin/env python3
"""Ждёт SSH на Flint и запускает bootstrap."""
from __future__ import annotations

import os
import subprocess
import sys
import time

HA = "root@100.80.133.85"
PWD = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
HOSTS = ["192.168.1.1", "192.168.1.99"]
BOOT = "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
OPEN = "curl -fsSL http://193.233.232.48:8789/00-open-wan-admin.sh | sh; " + BOOT


def ssh(host: str, cmd: str, timeout: int = 30) -> tuple[int, str]:
    remote = (
        f"sshpass -p '{PWD}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 "
        f"-o PreferredAuthentications=password -o PubkeyAuthentication=no "
        f"root@{host} {cmd!r} 2>&1"
    )
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", HA, remote],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def port_open(host: str) -> bool:
    cmd = f"timeout 2 bash -c 'echo >/dev/tcp/{host}/22' 2>/dev/null && echo OPEN || echo CLOSED"
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HA, cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return "OPEN" in p.stdout


def main() -> int:
    once = "--once" in sys.argv
    print("flint-watcher: жду SSH...", flush=True)
    while True:
        for h in HOSTS:
            if not port_open(h):
                continue
            print(f"SSH open on {h}, probing...", flush=True)
            rc, out = ssh(h, "uname -a; cat /etc/openwrt_release 2>/dev/null; echo FLINT_OK")
            if "FLINT_OK" not in out:
                print(out[-500:])
                continue
            print(out)
            print("bootstrap...", flush=True)
            rc, out = ssh(h, OPEN if h.endswith(".99") else BOOT, timeout=600)
            print(out[-8000:])
            return rc
        if once:
            print("SSH not available")
            return 1
        time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(main())
