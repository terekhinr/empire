#!/usr/bin/env python3
"""Keenetic telnet exec sh: проверка доступа к Flint с самого Keenetic."""
from __future__ import annotations

import os
import sys
import telnetlib
import time
from pathlib import Path


def load_env() -> None:
    p = Path("/root/.keenetic-admin.env")
    for line in p.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main() -> int:
    load_env()
    host = "192.168.1.1"
    login = os.environ.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = os.environ.get("KEENETIC_ADMIN_PASSWORD", "")
    cmd = (
        "curl -sI -m5 http://192.168.8.1/; "
        "curl -sI -m5 http://192.168.1.99/; "
        "ping -c2 -W2 192.168.8.1; "
        "ping -c2 -W2 192.168.1.99"
    )
    tn = telnetlib.Telnet(host, 23, timeout=25)
    tn.read_until(b"Login:", 15)
    tn.write(login.encode() + b"\n")
    tn.read_until(b"Password:", 15)
    tn.write(password.encode() + b"\n")
    time.sleep(2)
    tn.read_very_eager()
    tn.write(b"exec sh\r\n")
    time.sleep(4)
    boot = tn.read_very_eager().decode("utf-8", "replace")
    if "system failed" in boot.lower():
        print("EXEC_SH_FAIL", boot[-500:])
        return 2
    tn.write(cmd.encode() + b"\r\n")
    time.sleep(12)
    out = tn.read_very_eager().decode("utf-8", "replace")
    print(out[-4000:])
    tn.write(b"exit\r\n")
    tn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
