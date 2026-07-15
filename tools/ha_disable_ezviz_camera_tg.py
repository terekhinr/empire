#!/usr/bin/env python3
"""Удалить orphan entity registry для отключённых Ezviz→Telegram автоматизаций."""
from __future__ import annotations

import json
from pathlib import Path

REG = Path("/usr/share/hassio/homeassistant/.storage/core.entity_registry")
data = json.loads(REG.read_text(encoding="utf-8"))
ents = data["data"]["entities"]
keep = []
removed = []
for e in ents:
    eid = e.get("entity_id", "")
    uid = str(e.get("unique_id") or "")
    if eid.startswith("automation.ezviz_") or "empire_ezviz_motion" in uid:
        removed.append((eid, uid))
        continue
    keep.append(e)
print(f"remove {len(removed)}")
for eid, uid in removed:
    print(f"  {eid} {uid}")
if removed:
    data["data"]["entities"] = keep
    REG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("entity_registry patched")
else:
    print("nothing to remove")
