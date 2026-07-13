#!/usr/bin/env python3
"""Убрать зомби command_line и вернуть template на sensor.balkon_temperatura."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]
HA_HOST = "100.80.133.85"
HA_SSH_PORT = "22222"
REMOTE = "/config/.storage/core.entity_registry"
LOCAL = Path("/tmp/ha_er_balkon_fix.json")

ZOMBIE_CMD = {
    "sensor.balkon_temperatura",
    "sensor.balkon_vlazhnost",
    "sensor.balkon_batareia",
}
RENAME = {
    "sensor.balkon_temperatura_2": "sensor.balkon_temperatura",
    "sensor.balkon_vlazhnost_2": "sensor.balkon_vlazhnost",
    "sensor.balkon_batareia_2": "sensor.balkon_batareia",
}


def main() -> int:
    ssh_base = [
        "ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes",
        "-i", f"{Path.home()}/.ssh/id_ed25519", "-p", HA_SSH_PORT,
        f"root@{HA_HOST}",
    ]
    scp_down = [
        "scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes",
        "-i", f"{Path.home()}/.ssh/id_ed25519", "-P", HA_SSH_PORT,
        f"root@{HA_HOST}:{REMOTE}", str(LOCAL),
    ]
    subprocess.check_call(scp_down)

    store = json.loads(LOCAL.read_text())
    entities = store["data"]["entities"]
    before = len(entities)
    entities = [e for e in entities if e.get("entity_id") not in ZOMBIE_CMD]
    removed = before - len(entities)

    renamed = 0
    for ent in entities:
        old = ent.get("entity_id", "")
        if old in RENAME:
            ent["entity_id"] = RENAME[old]
            ent["original_name"] = ent.get("original_name") or old.split(".", 1)[-1].replace("_2", "")
            renamed += 1

    store["data"]["entities"] = entities
    LOCAL.write_text(json.dumps(store, indent=2))

    scp_up = [
        "scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes",
        "-i", f"{Path.home()}/.ssh/id_ed25519", "-P", HA_SSH_PORT,
        str(LOCAL), f"root@{HA_HOST}:{REMOTE}",
    ]
    subprocess.check_call(scp_up)
    print(f"removed command_line: {removed}, renamed template: {renamed}")

    subprocess.check_call(ssh_base + ["ha", "core", "restart"])
    print("HA restart sent — ждите ~90 с")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
