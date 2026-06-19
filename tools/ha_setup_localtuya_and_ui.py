#!/usr/bin/env python3
"""Создать LocalTuya (W602 + Smart plug), Lovelace Empire, yandex reload.

Запуск на armbian (рядом с devices.json):
  python3 ha_setup_localtuya_and_ui.py

Или с dev-машины:
  ssh root@100.80.133.85 'python3 -' < tools/ha_setup_localtuya_and_ui.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import tinytuya
except ImportError:
    print("Нужен tinytuya: ~/tinytuya-venv/bin/python", file=sys.stderr)
    sys.exit(2)

HA_CONFIG = Path(os.environ.get("HA_CONFIG", "/usr/share/hassio/homeassistant"))
DEVICES_JSON = Path(os.environ.get("DEVICES_JSON", "/root/devices.json"))
CONFIG_ENTRIES = HA_CONFIG / ".storage/core.config_entries"
ENTITY_REGISTRY = HA_CONFIG / ".storage/core.entity_registry"
DEVICE_REGISTRY = HA_CONFIG / ".storage/core.device_registry"
AREA_REGISTRY = HA_CONFIG / ".storage/core.area_registry"

HA_URL = os.environ.get("HA_URL", "http://127.0.0.1:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def dps_strings(status: dict) -> list[str]:
    dps = status.get("dps", status) if isinstance(status, dict) else {}
    if "dps" in dps:
        dps = dps["dps"]
    return [f"{k} (value: {v})" for k, v in sorted(dps.items(), key=lambda x: int(x[0]))]


def poll_device(dev: dict) -> dict:
    did, key, ip = dev["id"], dev["key"], dev["ip"]
    ver = dev.get("version") or "3.3"
    o = tinytuya.OutletDevice(did, ip, key, version=ver)
    o.set_socketTimeout(8)
    st = o.status()
    if not st or "Error" in str(st):
        raise RuntimeError(f"{dev.get('name')} @ {ip}: {st}")
    return st


def switch_entity(dp: int, friendly_name: str) -> dict:
    return {
        "id": dp,
        "platform": "switch",
        "friendly_name": friendly_name,
        "restore_on_reconnect": False,
        "is_passive_entity": False,
    }


def device_config(dev: dict, entities: list[dict], friendly: str) -> dict:
    st = poll_device(dev)
    return {
        "friendly_name": friendly,
        "host": dev["ip"],
        "device_id": dev["id"],
        "local_key": dev["key"],
        "protocol_version": dev.get("version") or "3.3",
        "enable_debug": False,
        "model": dev.get("model") or dev.get("product_name") or "Tuya",
        "product_name": dev.get("product_name") or "",
        "dps_strings": dps_strings(st),
        "entities": entities,
    }


def load_devices() -> dict[str, dict]:
    data = json.loads(DEVICES_JSON.read_text())
    return {d["id"]: d for d in data}


def upsert_localtuya_entry(devices_cfg: dict) -> str:
    store = json.loads(CONFIG_ENTRIES.read_text())
    entries = store["data"]["entries"]
    lt = next((e for e in entries if e.get("domain") == "localtuya"), None)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "region": "eu",
        "client_id": "",
        "client_secret": "",
        "user_id": "",
        "username": "localtuya",
        "no_cloud": True,
        "devices": devices_cfg,
        "updated_at": str(int(time.time() * 1000)),
    }
    if lt:
        lt["data"] = payload
        lt["modified_at"] = now
        entry_id = lt["entry_id"]
        print(f"  обновлён LocalTuya entry {entry_id}")
    else:
        entry_id = uuid.uuid4().hex[:26].upper()
        # HA uses ULID-like ids — generate similar
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        entry_id = "01" + "".join(random.choices(chars, k=24))
        entries.append(
            {
                "created_at": now,
                "data": payload,
                "disabled_by": None,
                "discovery_keys": {},
                "domain": "localtuya",
                "entry_id": entry_id,
                "minor_version": 1,
                "modified_at": now,
                "options": {},
                "pref_disable_new_entities": False,
                "pref_disable_polling": False,
                "source": "user",
                "subentries": [],
                "title": "localtuya",
                "unique_id": "localtuya_no_cloud",
                "version": 2,
            }
        )
        print(f"  создан LocalTuya entry {entry_id}")
    CONFIG_ENTRIES.write_text(json.dumps(store, indent=2))
    return entry_id


def area_id_by_name(name: str) -> str | None:
    if not AREA_REGISTRY.exists():
        return None
    store = json.loads(AREA_REGISTRY.read_text())
    for a in store.get("data", {}).get("areas", []):
        if a.get("name") == name:
            return a["id"]
    return None


def api_post(path: str, data: dict | None = None) -> None:
    if not HA_TOKEN:
        return
    import urllib.request

    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        f"{HA_URL}{path}",
        data=body,
        headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


def rename_entities(mapping: dict[str, str], area_names: dict[str, str]) -> None:
    """mapping: old_entity_id -> new_entity_id; area_names: new_entity_id -> area name."""
    if not ENTITY_REGISTRY.exists():
        return
    store = json.loads(ENTITY_REGISTRY.read_text())
    entities = store["data"]["entities"]
    for ent in entities:
        eid = ent.get("entity_id", "")
        if eid in mapping:
            new_id = mapping[eid]
            ent["entity_id"] = new_id
            print(f"  entity {eid} -> {new_id}")
        nid = ent.get("entity_id", "")
        if nid in area_names:
            aid = area_id_by_name(area_names[nid])
            if aid:
                ent["area_id"] = aid
    ENTITY_REGISTRY.write_text(json.dumps(store, indent=2))


def patch_configuration_yaml() -> bool:
    cfg = HA_CONFIG / "configuration.yaml"
    text = cfg.read_text()
    block = """
lovelace:
  mode: storage
  dashboards:
    empire-dashboard:
      mode: yaml
      title: Empire
      icon: mdi:home-heart
      show_in_sidebar: true
      require_admin: false
      filename: dashboards/empire_main.yaml
"""
    if "empire-dashboard" in text:
        print("  lovelace empire-dashboard уже в configuration.yaml")
        return False
    cfg.write_text(text.rstrip() + "\n" + block)
    print("  добавлен lovelace empire-dashboard в configuration.yaml")
    return True


def main() -> int:
    by_id = load_devices()
    w602 = by_id.get("28660000e868e78e310a")
    plug = by_id.get("bfcf3f474fc5d60919h3rz")
    if not w602 or not plug:
        print("devices.json: нет W602 или Smart plug", file=sys.stderr)
        return 1
    if not w602.get("ip") or not plug.get("ip"):
        print("Нет IP — сначала: tinytuya scan", file=sys.stderr)
        return 1

    print("==> LocalTuya: опрос устройств")
    devices_cfg = {
        w602["id"]: device_config(
            w602,
            [
                switch_entity(1, "Спальня свет один"),
                switch_entity(2, "Спальня свет два"),
            ],
            "W602 Спальня",
        ),
        plug["id"]: device_config(
            plug,
            [switch_entity(1, "Кухня чайник")],
            "Smart plug Кухня",
        ),
    }

    print("==> LocalTuya: запись config entry")
    upsert_localtuya_entry(devices_cfg)

    print("==> Lovelace dashboard")
    patch_configuration_yaml()

    print("==> Готово. Перезапустите HA: ha core restart")
    print("    После старта: переименовать entity при необходимости через API/UI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
