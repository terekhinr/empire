#!/usr/bin/env python3
"""Убрать устаревший YAML http: с HA (настройки уже в UI .storage/http)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ssh_opts() -> tuple[str, str, str]:
    return (
        os.environ.get("HA_SSH", "root@100.80.133.85"),
        os.environ.get("HA_SSH_PORT", "22222"),
        os.environ.get("HA_SSH_KEY", str(Path.home() / ".ssh/id_ed25519")),
    )


def scp(src: str, dst: str) -> None:
    host, port, key = ssh_opts()
    subprocess.run(
        ["scp", "-P", port, "-i", key, "-o", "BatchMode=yes", src, dst],
        check=True,
        capture_output=True,
    )


def ssh(cmd: str) -> str:
    host, port, key = ssh_opts()
    return subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-p", port, "-i", key, host, cmd],
        text=True,
    )


def strip_http_block(text: str) -> str:
    out: list[str] = []
    skip = False
    for line in text.splitlines(True):
        if skip:
            if line and not line[0].isspace() and not line.strip().startswith("#") and line.strip():
                skip = False
                out.append(line)
            continue
        if re.match(r"^http:\s*$", line):
            skip = True
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "".join(out).rstrip() + "\n")


def merge_proxies(data: dict) -> dict:
    stable = data["data"]["stable"]
    wanted = [
        "127.0.0.1/32",
        "::1/128",
        "192.168.1.1/32",
        "100.64.0.0/10",
        "172.30.32.0/23",
    ]
    merged: list[str] = []
    for item in wanted + list(stable.get("trusted_proxies") or []):
        if item not in merged:
            merged.append(item)
    stable["trusted_proxies"] = merged
    stable["use_x_forwarded_for"] = True
    data["data"]["pending"] = None
    return data


def main() -> int:
    load_env()
    host, _, _ = ssh_opts()
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "configuration.yaml"
        http_store = Path(tmp) / "http.json"
        scp(f"{host}:/homeassistant/configuration.yaml", str(cfg))
        scp(f"{host}:/homeassistant/.storage/http", str(http_store))
        cfg.write_text(strip_http_block(cfg.read_text()))
        if re.search(r"^http:", cfg.read_text(), re.M):
            raise SystemExit("http: still present")
        patched = merge_proxies(json.loads(http_store.read_text()))
        http_store.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n")
        scp(str(cfg), f"{host}:/homeassistant/configuration.yaml")
        scp(str(http_store), f"{host}:/homeassistant/.storage/http")
        print("trusted_proxies:", patched["data"]["stable"]["trusted_proxies"])
    print(ssh("ha core restart"))
    print("ha core restart issued")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
