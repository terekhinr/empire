#!/usr/bin/env python3
"""LocalTuya: новая розетка на кухню, старая на балкон, зоны и reload.

Запуск:
  cd /root/projects/empire && source .env
  python3 tools/ha_tuya_plugs_setup.py
  python3 tools/ha_tuya_plugs_setup.py --rename   # после reload: entity_id через WebSocket
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

EMPIRE_DIR = Path(__file__).resolve().parents[1]
LOCALTUYA_ENTRY = "01F1XRJS41AC54X2WPAEHVBMS1"

NEW_PLUG = {
    "id": "bfeceab6e6a9a092c9dm1t",
    "key": "}Xx&F6ZV1/[HT{pR",
    "ip": "192.168.1.143",
    "model": "LSP-16DL",
    "product_name": "Wifi Plug",
    "friendly_name": "Wifi Plug Кухня",
    "entity_name": "Кухня розетка",
    "entity_id": "switch.kuhnya_chainik",
    "area": "kukhnia",
    "device_name": "Wifi Plug Кухня",
}
OLD_PLUG = {
    "id": "bfcf3f474fc5d60919h3rz",
    "key": "c8}Dp9)e-!BEUl4D",
    "ip": "192.168.1.40",
    "model": "BP20V4",
    "product_name": "Smart plug",
    "friendly_name": "Smart plug Балкон",
    "entity_name": "Балкон мультиварка",
    "entity_id": "switch.balkon_multivarka",
    "area": "balkon",
    "device_name": "Smart plug Балкон",
}
W602_ID = "28660000e868e78e310a"


def switch_entity(dp: int, friendly_name: str) -> dict:
    return {
        "id": dp,
        "platform": "switch",
        "friendly_name": friendly_name,
        "restore_on_reconnect": False,
        "is_passive_entity": False,
    }


def plug_device_cfg(dev: dict, dps_strings: list[str]) -> dict:
    return {
        "friendly_name": dev["friendly_name"],
        "host": dev["ip"],
        "device_id": dev["id"],
        "local_key": dev["key"],
        "protocol_version": "3.3",
        "enable_debug": False,
        "model": dev["model"],
        "product_name": dev["product_name"],
        "dps_strings": dps_strings,
        "entities": [switch_entity(1, dev["entity_name"])],
    }


def ha_token() -> str:
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        env_path = EMPIRE_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("HA_TOKEN="):
                    token = line.split("=", 1)[1].strip()
    if not token:
        print("HA_TOKEN не задан", file=sys.stderr)
        sys.exit(2)
    return token


def ha_request(method: str, path: str, data: dict | None = None) -> dict | list | None:
    url = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/") + path
    token = ha_token()
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"HA API {path}: {e.code} {e.read().decode()[:500]}", file=sys.stderr)
        raise


def load_localtuya_devices(config_entries_path: Path) -> dict:
    store = json.loads(config_entries_path.read_text())
    lt = next(e for e in store["data"]["entries"] if e.get("domain") == "localtuya")
    return lt, store


def build_devices_cfg(lt_entry: dict) -> dict:
    existing = lt_entry["data"]["devices"]
    w602 = existing[W602_ID]
    new_dps = [
        "1 (value: True)",
        "9 (value: 0)",
        "18 (value: 0)",
        "19 (value: 0)",
        "20 (value: 0)",
        "21 (value: 1)",
        "22 (value: 0)",
        "23 (value: 0)",
        "24 (value: 0)",
        "25 (value: 0)",
        "26 (value: 0)",
    ]
    old_dps = existing.get(OLD_PLUG["id"], {}).get(
        "dps_strings",
        [
            "1 (value: False)",
            "9 (value: 0)",
            "18 (value: 0)",
            "19 (value: 0)",
            "20 (value: 0)",
            "21 (value: 1)",
            "22 (value: 0)",
            "23 (value: 0)",
            "24 (value: 0)",
            "25 (value: 0)",
            "26 (value: 0)",
            "38 (value: memory)",
            "39 (value: False)",
            "40 (value: relay)",
        ],
    )
    return {
        W602_ID: w602,
        NEW_PLUG["id"]: plug_device_cfg(NEW_PLUG, new_dps),
        OLD_PLUG["id"]: plug_device_cfg(OLD_PLUG, old_dps),
    }


def patch_entity_registry(path: Path) -> None:
    store = json.loads(path.read_text())
    entities = store["data"]["entities"]
    targets = {
        f"local_{NEW_PLUG['id']}_1": NEW_PLUG,
        f"local_{OLD_PLUG['id']}_1": OLD_PLUG,
    }
    seen: set[str] = set()
    for ent in entities:
        uid = ent.get("unique_id", "")
        if uid not in targets:
            continue
        cfg = targets[uid]
        ent["entity_id"] = cfg["entity_id"]
        ent["area_id"] = cfg["area"]
        ent["name"] = cfg["entity_name"].split()[-1] if " " in cfg["entity_name"] else cfg["entity_name"]
        ent["original_name"] = cfg["entity_name"]
        seen.add(uid)
        print(f"  entity {uid} → {cfg['entity_id']} ({cfg['area']})")
    # Снять старую привязку kitchen entity к offline device_id, если осталась
    for ent in entities:
        if ent.get("entity_id") == NEW_PLUG["entity_id"] and ent.get("unique_id") != f"local_{NEW_PLUG['id']}_1":
            ent["entity_id"] = f"switch.{NEW_PLUG['id']}_orphan"
            print(f"  orphan stale {ent.get('unique_id')}")
    if f"local_{NEW_PLUG['id']}_1" not in seen:
        print("  WARN: entity local_* новой розетки пока нет — появится после reload LocalTuya")
    path.write_text(json.dumps(store, indent=2))


async def ws_call(ws, mid: int, msg: dict) -> tuple[int, dict]:
    await ws.send(json.dumps({"id": mid, **msg}))
    while True:
        raw = json.loads(await ws.recv())
        if raw.get("id") == mid:
            return mid + 1, raw


async def rename_plug_entities() -> int:
    if websockets is None:
        print("pip install websockets", file=sys.stderr)
        return 1
    base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    token = ha_token()
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    mid = 1

    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            print("WebSocket auth failed", file=sys.stderr)
            return 1

        mid, ents_raw = await ws_call(ws, mid, {"type": "config/entity_registry/list"})
        mid, devs_raw = await ws_call(ws, mid, {"type": "config/device_registry/list"})
        entities = ents_raw.get("result", [])
        devices = devs_raw.get("result", [])

        by_uid = {e.get("unique_id"): e for e in entities}
        new_ent = by_uid.get(f"local_{NEW_PLUG['id']}_1")
        old_ent = by_uid.get(f"local_{OLD_PLUG['id']}_1")

        if old_ent and old_ent.get("entity_id") != OLD_PLUG["entity_id"]:
            mid, res = await ws_call(
                ws,
                mid,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": old_ent["entity_id"],
                    "new_entity_id": OLD_PLUG["entity_id"],
                    "area_id": OLD_PLUG["area"],
                    "name": "Мультиварка",
                },
            )
            print(f"  {old_ent['entity_id']} → {OLD_PLUG['entity_id']}: {res.get('success', res)}")

        if new_ent and new_ent.get("entity_id") != NEW_PLUG["entity_id"]:
            mid, res = await ws_call(
                ws,
                mid,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": new_ent["entity_id"],
                    "new_entity_id": NEW_PLUG["entity_id"],
                    "area_id": NEW_PLUG["area"],
                    "name": "Розетка",
                },
            )
            print(f"  {new_ent['entity_id']} → {NEW_PLUG['entity_id']}: {res.get('success', res)}")

        for dev in devices:
            ident = str(dev.get("identifiers", ""))
            if NEW_PLUG["id"] in ident or f"local_{NEW_PLUG['id']}" in ident:
                mid, res = await ws_call(
                    ws,
                    mid,
                    {
                        "type": "config/device_registry/update",
                        "device_id": dev["id"],
                        "area_id": NEW_PLUG["area"],
                        "name_by_user": NEW_PLUG["device_name"],
                    },
                )
                print(f"  device NEW area: {res.get('success', res)}")
            elif OLD_PLUG["id"] in ident or f"local_{OLD_PLUG['id']}" in ident:
                mid, res = await ws_call(
                    ws,
                    mid,
                    {
                        "type": "config/device_registry/update",
                        "device_id": dev["id"],
                        "area_id": OLD_PLUG["area"],
                        "name_by_user": OLD_PLUG["device_name"],
                    },
                )
                print(f"  device OLD area: {res.get('success', res)}")

    states = ha_request("GET", "/api/states")
    for eid in (NEW_PLUG["entity_id"], OLD_PLUG["entity_id"]):
        st = next((s for s in states if s["entity_id"] == eid), None)
        print(f"  {eid}: {st['state'] if st else 'missing'}")
    return 0


def patch_device_registry(path: Path) -> None:
    store = json.loads(path.read_text())
    for dev in store["data"]["devices"]:
        ids = str(dev.get("identifiers", ""))
        if NEW_PLUG["id"] in ids or f"local_{NEW_PLUG['id']}" in ids:
            dev["name"] = NEW_PLUG["device_name"]
            dev["area_id"] = NEW_PLUG["area"]
            print(f"  device NEW → {NEW_PLUG['area']}")
        elif OLD_PLUG["id"] in ids or f"local_{OLD_PLUG['id']}" in ids:
            dev["name"] = OLD_PLUG["device_name"]
            dev["area_id"] = OLD_PLUG["area"]
            print(f"  device OLD → {OLD_PLUG['area']}")
    path.write_text(json.dumps(store, indent=2))


def main() -> int:
    config_path = Path(os.environ.get("HA_CONFIG_ENTRIES", "/tmp/ha_config_entries.json"))
    entity_path = Path(os.environ.get("HA_ENTITY_REGISTRY", "/tmp/ha_entity_registry.json"))
    device_path = Path(os.environ.get("HA_DEVICE_REGISTRY", "/tmp/ha_device_registry.json"))
    reload = os.environ.get("HA_RELOAD", "1") == "1"
    patch_only = os.environ.get("HA_PATCH_ONLY", "0") == "1"

    if not config_path.exists():
        print(f"Нет {config_path} — сначала scp с HA", file=sys.stderr)
        return 1

    if not patch_only:
        lt, store = load_localtuya_devices(config_path)
        lt["data"]["devices"] = build_devices_cfg(lt)
        lt["data"]["updated_at"] = str(int(time.time() * 1000))
        lt["modified_at"] = datetime.now(timezone.utc).isoformat()
        config_path.write_text(json.dumps(store, indent=2))
        print("==> LocalTuya: 3 устройства (W602 + кухня .51 + балкон .40)")

    if entity_path.exists():
        print("==> Entity registry")
        patch_entity_registry(entity_path)
    if device_path.exists():
        print("==> Device registry")
        patch_device_registry(device_path)

    if reload:
        print("==> Reload LocalTuya entry")
        ha_request("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": LOCALTUYA_ENTRY})
        time.sleep(10)
        states = ha_request("GET", "/api/states")
        for eid in (NEW_PLUG["entity_id"], OLD_PLUG["entity_id"]):
            st = next((s for s in states if s["entity_id"] == eid), None)
            if st:
                print(f"  {eid}: {st['state']}")
            else:
                print(f"  {eid}: not found yet")
        print("==> Reload automations")
        ha_request("POST", "/api/services/automation/reload")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rename", action="store_true", help="Переименовать entity через WebSocket")
    args = parser.parse_args()
    if args.rename:
        raise SystemExit(asyncio.run(rename_plug_entities()))
    raise SystemExit(main())
