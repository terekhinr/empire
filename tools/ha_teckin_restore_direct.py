#!/usr/bin/env python3
"""Вернуть Teckin на прямой RTSP (откат go2rtc) + flip 180° на камере."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]

CAMERAS = {
    "01KVWABNDDHAQ09RB9A3HSV9ZY": ("192.168.1.34", "1"),
    "01KVWBAEFZTVY274BA6HBCRNQE": ("192.168.1.84", "2"),
}


def load_env() -> None:
    p = EMPIRE_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def build_options(ip: str, pwd: str = "pass") -> dict:
    return {
        "stream_source": f"rtsp://{ip}:554/video0_unicast",
        "still_image_url": f"https://{ip}/cgi-bin/currentpic.cgi",
        "username": "root",
        "password": pwd,
        "content_type": "image/jpeg",
        "advanced": {
            "authentication": "basic",
            "framerate": 2,
            "rtsp_transport": "tcp",
            "verify_ssl": False,
        },
    }


def main() -> int:
    load_env()
    pwd = os.environ.get("TECKIN_PASS", "pass")
    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    ssh = ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, ha_host]
    scp = ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port]

    tmp = Path(tempfile.gettempdir()) / "ha_ce_restore.json"
    subprocess.run([*scp, f"{ha_host}:/config/.storage/core.config_entries", str(tmp)], check=True)
    ce = json.loads(tmp.read_text())
    for e in ce["data"]["entries"]:
        entry_id = e.get("entry_id")
        if entry_id not in CAMERAS:
            continue
        ip, _slot = CAMERAS[entry_id]
        e["options"] = build_options(ip, pwd)
        e["title"] = ip.replace(".", "_")
        print(f"✓ {entry_id} → прямой RTSP {ip}")
    tmp.write_text(json.dumps(ce, indent=2))
    subprocess.run([*scp, str(tmp), f"{ha_host}:/config/.storage/core.config_entries"], check=True)

    py = str(EMPIRE_DIR / "venv/bin/python3")
    if not Path(py).exists():
        py = sys.executable
    for slot in ("1", "2"):
        print(f"==> flip=1 slot {slot}")
        subprocess.run([py, str(EMPIRE_DIR / "tools/ha_teckin_fix.py"), "--slot", slot, "--flip", "1"], check=False)

    print("==> ha core restart")
    subprocess.run([*ssh, "ha core restart"], check=True, timeout=180)
    print("Готово: прямой RTSP + аппаратный flip. Ctrl+Shift+R")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
