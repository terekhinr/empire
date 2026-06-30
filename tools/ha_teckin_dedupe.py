#!/usr/bin/env python3
"""Оставить одну интеграцию generic для Teckin (192.168.1.84). Запуск на VPS после scp storage с HA."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KEEP_ENTITY = "camera.teckin_tc100"
CAMERA_IP = "192.168.1.84"


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} core.config_entries core.entity_registry", file=sys.stderr)
        return 2
    ce_path, er_path = Path(sys.argv[1]), Path(sys.argv[2])
    reg = json.loads(er_path.read_text())
    keep_entry = None
    for ent in reg["data"]["entities"]:
        if ent.get("entity_id") == KEEP_ENTITY:
            keep_entry = ent.get("config_entry_id")
            break
    if not keep_entry:
        print(f"entity {KEEP_ENTITY} not in registry", file=sys.stderr)
        return 1

    ce = json.loads(ce_path.read_text())
    entries = ce["data"]["entries"]
    removed = []
    kept = []
    for e in entries:
        if e.get("domain") != "generic":
            kept.append(e)
            continue
        opts = e.get("options") or {}
        src = str(opts.get("stream_source", ""))
        if e.get("entry_id") == keep_entry or CAMERA_IP in src:
            if e.get("entry_id") == keep_entry:
                kept.append(e)
            else:
                removed.append(e["entry_id"])
        else:
            kept.append(e)
    ce["data"]["entries"] = kept
    ents = [e for e in reg["data"]["entities"] if e.get("entity_id") != KEEP_ENTITY or e.get("config_entry_id") == keep_entry]
    reg["data"]["entities"] = [e for e in ents if not (e.get("entity_id", "").startswith("camera.192_168_1_84") and e.get("entity_id") != KEEP_ENTITY)]
    ce_path.write_text(json.dumps(ce, indent=2))
    er_path.write_text(json.dumps(reg, indent=2))
    print(f"kept entry {keep_entry}, removed {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
