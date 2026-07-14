#!/usr/bin/env python3
"""HA: static ARP Flint LAN MAC → SSH bootstrap на 192.168.1.1."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

FLINT_LAN_MAC = "94:83:c4:df:8a:b4"
FLINT_IP = "192.168.1.1"
HA = "root@100.80.133.85"


def load_env() -> None:
    p = Path("/root/.flint-admin.env")
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ha(cmd: str, timeout: int = 300) -> tuple[int, str, str]:
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HA, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    load_env()
    fp = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
    bootstrap = (
        "export KEENETIC_WIFI_SSID=Destroy KEENETIC_WIFI_PSK=p0tertiy "
        "FLINT2_BASE=http://193.233.232.48:8789; "
        "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
    )
    bs_q = bootstrap.replace("'", "'\"'\"'")

    script = f"""
set -e
DEV=eth0
MAC={FLINT_LAN_MAC}
IP={FLINT_IP}
FP='{fp}'
echo '=== before ==='
ip neigh show {FLINT_IP} || true
curl -sI -m4 http://{FLINT_IP}/ 2>&1 | head -3 || true
echo '=== static arp flint lan ==='
ip neigh replace $IP lladdr $MAC dev $DEV nud permanent || ip neigh add $IP lladdr $MAC dev $DEV nud permanent
sleep 1
echo '=== after arp ==='
ip neigh show $IP
curl -sI -m6 http://$IP/ 2>&1 | head -8 || true
echo '=== ssh probe ==='
sshpass -p "$FP" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null root@$IP 'uname -a; uci get network.lan.ipaddr; echo SSH_OK' 2>&1 | head -20
echo '=== bootstrap ==='
sshpass -p "$FP" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o UserKnownHostsFile=/dev/null root@$IP '{bs_q}' 2>&1 | tail -50
echo BOOT_RC=$?
echo '=== restore arp (delete static) ==='
ip neigh del $IP dev $DEV 2>/dev/null || true
"""
    rc, out, err = ha(script, timeout=600)
    print(out)
    if err:
        print(err[-2000:])
    return 0 if "BOOT_RC=0" in out or "[flint2]" in out or "SSH_OK" in out else rc


if __name__ == "__main__":
    raise SystemExit(main())
