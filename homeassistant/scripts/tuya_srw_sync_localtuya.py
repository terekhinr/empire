#!/usr/bin/env python3
"""После discover: прописать IP SRW в LocalTuya (core.config_entries). Запуск на HA."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRW_ID = "bf86f3c7f53b7bb055f6x2"
LOCALTUYA_ENTRY = "01F1XRJS41AC54X2WPAEHVBMS1"
LOCAL = Path(__file__).with_name(".srw_local.json")
STORE = Path("/config/.storage/core.config_entries")


def main() -> int:
    if not LOCAL.exists():
        print("no .srw_local.json")
        return 1
    cfg = json.loads(LOCAL.read_text())
    ip = (cfg.get("ip") or "").strip()
    key = cfg.get("local_key") or ""
    ver = cfg.get("version") or "3.3"
    if not key:
        print("no local_key")
        return 1
    if not ip or ip in ("0.0.0.0", "127.0.0.1"):
        print(f"no valid ip ({ip})")
        return 1

    if not STORE.exists():
        print("no config_entries")
        return 1

    store = json.loads(STORE.read_text())
    lt = next(e for e in store["data"]["entries"] if e.get("entry_id") == LOCALTUYA_ENTRY)
    dev = lt["data"]["devices"].setdefault(SRW_ID, {})
    dev["friendly_name"] = dev.get("friendly_name") or "SRW-TH01 Балкон"
    dev["host"] = ip
    dev["device_id"] = SRW_ID
    dev["local_key"] = key
    dev["protocol_version"] = ver
    dev["scan_interval"] = 300
    dev["device_sleep_time"] = 300
    dev.setdefault("entities", [
        {"id": "1", "platform": "sensor", "friendly_name": "Балкон t° raw", "device_class": "temperature",
         "unit_of_measurement": "°C", "state_class": "measurement", "scaling": 0.1, "is_passive_entity": True},
        {"id": "2", "platform": "sensor", "friendly_name": "Балкон влажн raw", "device_class": "humidity",
         "unit_of_measurement": "%", "state_class": "measurement", "is_passive_entity": True},
        {"id": "4", "platform": "sensor", "friendly_name": "Балкон батарея raw", "device_class": "battery",
         "unit_of_measurement": "%", "state_class": "measurement", "entity_category": "diagnostic", "is_passive_entity": True},
    ])
    lt["data"]["updated_at"] = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    STORE.write_text(json.dumps(store, indent=2))
    print(f"synced LocalTuya SRW @ {ip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
