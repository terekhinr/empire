#!/usr/bin/env python3
"""Heal Keenetic via HA shell_command (if deployed). Uses HA_TOKEN from env files."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

HEAL_CMD = (
    "export PATH=/opt/bin:/opt/sbin:$PATH; "
    "curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh"
)
ROUTER_SSH = (
    "sshpass -p keenetic ssh -o StrictHostKeyChecking=no -p 222 root@192.168.1.1 "
    + json.dumps(HEAL_CMD)
)


def load_env() -> None:
    for p in (
        Path("/root/.env"),
        Path("/root/projects/empire/.env"),
        Path("/etc/empire/ha.env"),
    ):
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ha_call(url: str, token: str, path: str, data: dict | None = None) -> tuple[int, str]:
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")[:500]


def main() -> int:
    load_env()
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        print("NO_HA_TOKEN")
        return 2
    for base in (
        "https://ha.potertiy.keenetic.pro",
        os.environ.get("HA_URL", "").rstrip("/"),
        "http://192.168.1.41:8123",
    ):
        if not base:
            continue
        try:
            st, _ = ha_call(base, token, "/api/")
            print(f"HA_OK {base} status={st}")
        except Exception as exc:
            print(f"HA_FAIL {base} {exc}")
            continue
        for svc in (
            "shell_command.keenetic_heal",
            "shell_command.heal_router",
            "shell_command.router_heal",
        ):
            try:
                st, body = ha_call(
                    base,
                    token,
                    f"/api/services/{svc.replace('.', '/')}",
                    {},
                )
                print(f"SERVICE_OK {svc} status={st} {body[:200]}")
                return 0
            except urllib.error.HTTPError as exc:
                print(f"SERVICE_HTTP {svc} {exc.code}")
            except Exception as exc:
                print(f"SERVICE_FAIL {svc} {exc}")
    print("ALL_PATHS_FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
