#!/usr/bin/env python3
"""VPS: ждёт SSH на Flint (через HA + Keenetic) и запускает bootstrap."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HA = "root@100.80.133.85"
KEEN = ("admin", "192.168.1.1", 222)
FLINT_HOSTS = ("192.168.1.99", "192.168.1.1", "2a00:1370:8198:34bd:9683:c4ff:fedf:8ab2")
FLINT_LAN_MAC = "94:83:c4:df:8a:b4"
BOOT = (
    "export KEENETIC_WIFI_SSID=Destroy KEENETIC_WIFI_PSK=p0tertiy "
    "FLINT2_BASE=http://193.233.232.48:8789; "
    "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
)


def load_env() -> None:
    for p in (Path("/root/.flint-admin.env"), Path("/root/.keenetic-admin.env")):
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ha(cmd: str, timeout: int = 30) -> str:
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", HA, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return (p.stdout or "") + (p.stderr or "")


def keenetic_sh(body: str, wait: int = 120) -> str:
    kp = os.environ.get("KEENETIC_ADMIN_PASSWORD", "3ur6agan")
    user, host, port = KEEN
    inner = body.replace("'", "'\"'\"'")
    cmd = (
        f"sshpass -p '{kp}' ssh -T -o StrictHostKeyChecking=no -p {port} {user}@{host} "
        f"\"exec sh\" <<'EOS'\n{inner}\nexit\nEOS"
    )
    return ha(cmd, timeout=wait + 30)


def port_open(host: str) -> bool:
    if ":" in host:
        check = f"(echo >/dev/tcp/{host}/22) 2>/dev/null && echo OPEN || echo CLOSED"
        return "OPEN" in keenetic_sh(f"export PATH=/opt/bin:/opt/sbin:$PATH; {check}", wait=8)
    out = ha(
        f"timeout 3 bash -c 'echo >/dev/tcp/{host}/22' 2>/dev/null && echo OPEN || echo CLOSED",
        timeout=10,
    )
    if "OPEN" in out:
        return True
    # ARP override for Flint LAN on .1
    if host == "192.168.1.1":
        out = ha(
            f"ip neigh replace {host} lladdr {FLINT_LAN_MAC} dev eth0 nud permanent; "
            f"timeout 3 bash -c 'echo >/dev/tcp/{host}/22' 2>/dev/null && echo OPEN || echo CLOSED; "
            f"ip neigh del {host} dev eth0 2>/dev/null || true",
            timeout=10,
        )
    return "OPEN" in out


def run_bootstrap(host: str) -> bool:
    fp = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
    br = host if ":" not in host else f"[{host}]"
    body = (
        "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH\n"
        f"FP={fp!r}\nBS={BOOT!r}\nH={br!r}\n"
        "( sleep 1; echo \"$FP\"; sleep 2 ) | dbclient -y root@$H \"$BS\"\n"
        "echo RC=$?\n"
    )
    out = keenetic_sh(body, wait=300)
    print(out[-10000:])
    return "RC=0" in out or "[flint2]" in out


def run_bootstrap_ha(host: str) -> bool:
    fp = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
    prep = ""
    if host == "192.168.1.1":
        prep = f"ip neigh replace {host} lladdr {FLINT_LAN_MAC} dev eth0 nud permanent; "
    cmd = (
        f"{prep}sshpass -p '{fp}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "
        f"-o UserKnownHostsFile=/dev/null root@{host} {BOOT!r}; "
        f"ip neigh del {host} dev eth0 2>/dev/null || true"
    )
    out = ha(cmd, timeout=600)
    print(out[-10000:])
    return "[flint2]" in out or "готово" in out


def main() -> int:
    load_env()
    once = "--once" in sys.argv
    print("flint2-watcher: polling SSH on Flint...", flush=True)
    while True:
        for h in FLINT_HOSTS:
            if not port_open(h):
                continue
            print(f"port 22 open on {h}", flush=True)
            if run_bootstrap_ha(h) or run_bootstrap(h):
                print("bootstrap OK", flush=True)
                return 0
        if once:
            print("SSH not available on Flint", flush=True)
            return 1
        time.sleep(25)


if __name__ == "__main__":
    raise SystemExit(main())
