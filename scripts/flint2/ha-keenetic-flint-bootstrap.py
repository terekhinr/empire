#!/usr/bin/env python3
"""HA → Keenetic Entware :222 → Flint (dbclient/openssh)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

FLINT_HOSTS = ("192.168.1.99", "192.168.1.1", "2a00:1370:8198:34bd:9683:c4ff:fedf:8ab2")


def load_env() -> None:
    for p in (Path("/root/.flint-admin.env"), Path("/root/.keenetic-admin.env")):
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ha_ssh(cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def keenetic_entware(remote: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    rp = os.environ.get("KEENETIC_ROUTER_PASS", "keenetic")
    inner = remote.replace("'", "'\"'\"'")
    cmd = (
        f"sshpass -p '{rp}' ssh -T -o StrictHostKeyChecking=no -o ConnectTimeout=12 "
        f"-p 222 root@192.168.1.1 '{inner}'"
    )
    return ha_ssh(cmd, timeout=timeout)


def main() -> int:
    load_env()
    fp = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
    bootstrap = (
        "export KEENETIC_WIFI_SSID=Destroy KEENETIC_WIFI_PSK=p0tertiy "
        "FLINT2_BASE=http://193.233.232.48:8789; "
        "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
    )

    print("=== Entware on Keenetic ===")
    p = keenetic_entware(
        "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
        "uname -a; which dbclient dropbear ssh curl wget 2>/dev/null",
        timeout=30,
    )
    print(p.stdout)
    if p.stderr:
        print(p.stderr[-500:])

    for host in FLINT_HOSTS:
        br = host if ":" not in host else f"[{host}]"
        print(f"=== probe {host} ===")
        probe = (
            "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
            f"H={br}; "
            "wget -qO- -T6 http://$H/ 2>&1 | head -3; "
            "(echo >/dev/tcp/${H#[}]/22) 2>/dev/null && echo tcp22=open || echo tcp22=closed"
        )
        print(keenetic_entware(probe, timeout=25).stdout[-2000:])

        print(f"=== bootstrap via dbclient {host} ===")
        run = (
            "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
            f"FP={fp!r}; BS={bootstrap!r}; H={br!r}; "
            f"( sleep 1; echo \"$FP\"; sleep 1 ) | dbclient -y root@$H \"$BS\" 2>&1; "
            "echo DB_RC=$?"
        )
        out = keenetic_entware(run, timeout=300)
        print(out.stdout[-6000:])
        if out.stderr:
            print(out.stderr[-500:])
        if "DB_RC=0" in out.stdout or "[flint2]" in out.stdout:
            return 0

        print(f"=== bootstrap via sshpass {host} ===")
        run2 = (
            "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
            f"FP={fp!r}; BS={bootstrap!r}; H={br!r}; "
            f"sshpass -p \"$FP\" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "
            f"root@$H \"$BS\" 2>&1; echo SSH_RC=$?"
        )
        out2 = keenetic_entware(run2, timeout=300)
        print(out2.stdout[-6000:])
        if "SSH_RC=0" in out2.stdout or "[flint2]" in out2.stdout:
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
