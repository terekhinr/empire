#!/usr/bin/env python3
"""Keenetic Entware :222 → curl bootstrap на Flint по SSH если открыт."""
from __future__ import annotations

import os
import subprocess
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
    rp = os.environ.get("KEENETIC_ROUTER_PASS", "keenetic")
    bootstrap = "http://193.233.232.48:8789/00-bootstrap.sh"
    inner = (
        "export PATH=/opt/bin:/opt/sbin:$PATH; "
        "ip addr add 192.168.8.254/24 dev br0 2>/dev/null || true; "
        "ping -c1 -W2 192.168.8.1; "
        f"/opt/bin/curl -sI -m8 http://192.168.8.1/ | head -5; "
        f"/opt/bin/curl -fsSL {bootstrap} | /opt/bin/curl -fsSL http://192.168.8.1/ 2>/dev/null; "
        "echo TRY_SSH; "
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@192.168.8.1 '{bootstrap} | sh' 2>&1 | head -5"
    )
    cmd = (
        f"sshpass -p '{rp}' ssh -T -o ConnectTimeout=15 -o StrictHostKeyChecking=no "
        f"root@100.80.133.85 \"sshpass -p '{rp}' ssh -T -o ConnectTimeout=12 -o StrictHostKeyChecking=no "
        f"-p 222 root@192.168.1.1 '{inner}'\""
    )
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    print(p.stdout)
    print(p.stderr)
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
