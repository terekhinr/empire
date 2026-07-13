#!/usr/bin/env python3
"""DEPRECATED: go2rtc rotate ломает поток (чёрный экран). Используй ha_teckin_restore_direct.py"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]

STREAMS = {
    "01KVWABNDDHAQ09RB9A3HSV9ZY": "teckin_kuhnya",
    "01KVWBAEFZTVY274BA6HBCRNQE": "teckin_max",
}


def load_env() -> None:
    env_path = EMPIRE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_env()
    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    ssh = ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, ha_host]
    scp = ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port]

    print("==> go2rtc.yaml")
    subprocess.run(
        [*scp, str(EMPIRE_DIR / "homeassistant/go2rtc.yaml"), f"{ha_host}:/config/go2rtc.yaml"],
        check=True,
    )

    tmp = Path(tempfile.gettempdir()) / "ha_ce_go2rtc.json"
    subprocess.run([*scp, f"{ha_host}:/config/.storage/core.config_entries", str(tmp)], check=True)
    ce = json.loads(tmp.read_text())
    for e in ce["data"]["entries"]:
        entry_id = e.get("entry_id")
        stream = STREAMS.get(entry_id)
        if not stream:
            continue
        opts = e.setdefault("options", {})
        opts["stream_source"] = f"rtsp://127.0.0.1:8554/{stream}"
        opts["still_image_url"] = f"http://127.0.0.1:1984/api/frame.jpeg?src={stream}"
        opts.setdefault("advanced", {})["rtsp_transport"] = "tcp"
        print(f"✓ {entry_id} → go2rtc/{stream}")
    tmp.write_text(json.dumps(ce, indent=2))
    subprocess.run([*scp, str(tmp), f"{ha_host}:/config/.storage/core.config_entries"], check=True)

    print("==> аппаратный flip=0 (поворот только в go2rtc)")
    subprocess.run(
        [sys.executable, str(EMPIRE_DIR / "tools/ha_teckin_fix.py"), "--slot", "1", "--flip", "0"],
        check=False,
    )
    subprocess.run(
        [sys.executable, str(EMPIRE_DIR / "tools/ha_teckin_fix.py"), "--slot", "2", "--flip", "0"],
        check=False,
    )

    print("==> dashboard")
    subprocess.run(
        [*scp, str(EMPIRE_DIR / "homeassistant/dashboards/empire_wall.yaml"), f"{ha_host}:/config/dashboards/empire_wall.yaml"],
        check=True,
    )

    print("==> ha core restart")
    subprocess.run([*ssh, "ha core restart"], check=True, timeout=180)
    print("Готово. Ctrl+Shift+R → /empire-wall/kamery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
