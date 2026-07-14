#!/usr/bin/env python3
"""Bootstrap Flint через Keenetic shell: SSH на WAN 192.168.1.99 или LAN .1."""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

FLINT_HOSTS = ("192.168.1.99", "192.168.1.1", "2a00:1370:8198:34bd:9683:c4ff:fedf:8ab2")


def load_env() -> None:
    for p in (
        Path("/root/.flint-admin.env"),
        Path("/root/.keenetic-admin.env"),
    ):
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def keenetic_exec(shell_cmd: str, wait: int = 90) -> str:
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    kpass = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    script = textwrap.dedent(
        f"""
        import telnetlib, time
        tn=telnetlib.Telnet("192.168.1.1", 23, timeout=25)
        tn.read_until(b"Login:", 15); tn.write({login!r}.encode()+b"\\n")
        tn.read_until(b"Password:", 15); tn.write({kpass!r}.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(3)
        tn.read_very_eager(); tn.write({shell_cmd!r}.encode()+b"\\r\\n"); time.sleep({wait})
        out=tn.read_very_eager().decode("utf-8", "replace")
        print(out[-12000:])
        tn.write(b"exit\\r\\n"); tn.close()
        """
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=wait + 60,
    )
    return p.stdout.decode()


def main() -> int:
    load_env()
    fp = os.environ.get("FLINT_ADMIN_PASSWORD", "3ur6agan")
    bootstrap = (
        "export KEENETIC_WIFI_SSID=Destroy KEENETIC_WIFI_PSK=p0tertiy "
        "FLINT2_BASE=http://193.233.232.48:8789; "
        "curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
    )
    hosts = " ".join(FLINT_HOSTS)
    probe = (
        "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
        f"FP={fp!r}; BS={bootstrap!r}; "
        "echo PROBE_START; "
        f"for H in {hosts}; do "
        "  echo === host $H ===; "
        "  wget -qO- -T6 http://[$H]/ 2>/dev/null | head -2 || wget -qO- -T6 http://$H/ 2>&1 | head -2; "
        "  printf '' | nc $H 22 2>/dev/null | head -1; "
        "done"
    )
    print("=== PROBE ===")
    print(keenetic_exec(probe, wait=25))

    for host in FLINT_HOSTS:
        br = host if ":" not in host else f"[{host}]"
        ssh_cmd = (
            "export PATH=/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH; "
            f"FP={fp!r}; BS={bootstrap!r}; H={br!r}; "
            "printf '%s\\n' '#!/bin/sh' \"echo $FP\" > /tmp/fap; chmod +x /tmp/fap; "
            "DISPLAY=:0 SSH_ASKPASS=/tmp/fap SSH_ASKPASS_REQUIRE=force "
            "/opt/bin/ssh -oNumberOfPasswordPrompts=1 -o PreferredAuthentications=password "
            "-o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=15 "
            f"root@$H \"$BS\" 2>&1 | tail -40; echo SSH_RC=$?"
        )
        print(f"=== BOOTSTRAP via {host} ===")
        out = keenetic_exec(ssh_cmd, wait=180)
        print(out)
        if "SSH_RC=0" in out or "bootstrap done" in out.lower() or "podkop" in out.lower():
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
