#!/usr/bin/env python3
"""Датчик газа Tuya _TZE284_chbyv06x: диагностика и настройка через HA API.

Запуск:
  cd /root/projects/empire && set -a && source .env && set +a
  python3 tools/ha_gas_sensor_setup.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

try:
    import websockets
except ImportError:
    print("pip install websockets", file=sys.stderr)
    sys.exit(1)

GAS_MANUFACTURER = "_TZE284_chbyv06x"
GAS_MODEL = "TS0601"
GAS_DEVICE_NAME = "Датчик газа"
GAS_AREA = "Кухня"
EXPECTED_GAS_ENTITY = "binary_sensor.balkon_datchik_gaza"


async def ws_call(ws, mid: int, msg: dict) -> tuple[int, dict]:
    await ws.send(json.dumps({"id": mid, **msg}))
    while True:
        raw = json.loads(await ws.recv())
        if raw.get("id") == mid:
            return mid + 1, raw


async def main() -> int:
    base = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not base or not token:
        print("Нужны HA_URL и HA_TOKEN", file=sys.stderr)
        return 1

    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    mid = 1

    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print("auth failed:", auth, file=sys.stderr)
            return 1

        mid, areas_raw = await ws_call(ws, mid, {"type": "config/area_registry/list"})
        areas = areas_raw.get("result", [])
        kuhnya = next((a for a in areas if a.get("name") == GAS_AREA), None)
        if not kuhnya:
            print(f"Область «{GAS_AREA}» не найдена", file=sys.stderr)
            return 1

        mid, devs_raw = await ws_call(ws, mid, {"type": "config/device_registry/list"})
        mid, ents_raw = await ws_call(ws, mid, {"type": "config/entity_registry/list"})
        mid, zha_raw = await ws_call(ws, mid, {"type": "zha/devices"})

        devices = devs_raw.get("result", [])
        entities = ents_raw.get("result", [])
        zha_devices = zha_raw.get("result", [])

        gas_dev = None
        gas_zha = None
        for d in devices:
            if d.get("manufacturer") == GAS_MANUFACTURER and d.get("model") == GAS_MODEL:
                gas_dev = d
                break
        for d in zha_devices:
            if d.get("manufacturer") == GAS_MANUFACTURER and d.get("model") == GAS_MODEL:
                gas_zha = d
                break

        if not gas_dev and not gas_zha:
            print(f"Устройство {GAS_MANUFACTURER} {GAS_MODEL} не найдено в ZHA.")
            print("ZHA → Добавить устройство → удерживайте кнопку на датчике 5–10 с.")
            return 1

        dev_id = (gas_dev or {}).get("id") or gas_zha.get("device_reg_id")
        print(f"Устройство: {GAS_MANUFACTURER} {GAS_MODEL}")
        print(f"  device_id: {dev_id}")
        if gas_zha:
            print(f"  ieee: {gas_zha.get('ieee')}")
            print(f"  quirk_applied: {gas_zha.get('quirk_applied')}")
            print(f"  quirk_class: {gas_zha.get('quirk_class')}")
            print(f"  available: {gas_zha.get('available')}")
            print(f"  entities: {[e.get('entity_id') for e in gas_zha.get('entities', [])]}")

        mid, upd = await ws_call(
            ws,
            mid,
            {
                "type": "config/device_registry/update",
                "device_id": dev_id,
                "area_id": kuhnya["area_id"],
                "name_by_user": GAS_DEVICE_NAME,
            },
        )
        if upd.get("success"):
            print(f"Область: «{GAS_AREA}», имя: «{GAS_DEVICE_NAME}»")
        else:
            print("Не удалось обновить device_registry:", upd.get("error"))

        gas_entities = [
            e
            for e in entities
            if e.get("device_id") == dev_id and e.get("entity_id", "").startswith("binary_sensor.")
        ]
        gas_on = [e for e in gas_entities if e.get("entity_id") == EXPECTED_GAS_ENTITY]

        if gas_zha and not gas_zha.get("quirk_applied"):
            print()
            print("ПРОБЛЕМА: quirk не применён — сущности газа нет.")
            print("Решение:")
            print("  bash deploy/ha_deploy_gas_sensor.sh   # или quirk вручную в File editor")
            print("  Перезапуск HA → ZHA: удалить устройство → добавить снова")
        elif gas_on:
            print(f"OK: {EXPECTED_GAS_ENTITY} зарегистрирован")
        else:
            print(f"binary_sensor газа пока нет (ожидается {EXPECTED_GAS_ENTITY})")

        mid, autos_raw = await ws_call(ws, mid, {"type": "config/entity_registry/list"})
        # automation entities are not in entity registry the same way; check state via REST below

    import urllib.request

    req = urllib.request.Request(
        f"{base}/api/states/automation.gaz_telegram",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print("Автоматизация automation.gaz_telegram: есть")
    except Exception:
        req2 = urllib.request.Request(
            f"{base}/api/states",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req2, timeout=15) as r:
            states = json.loads(r.read().decode())
        gas_auto = [s for s in states if s["entity_id"].startswith("automation.") and "газ" in s["attributes"].get("friendly_name", "").lower()]
        if gas_auto:
            print(f"Автоматизация: {gas_auto[0]['entity_id']}")
        else:
            print("Автоматизация «Газ — Telegram»: задеплойте empire_telegram.yaml и Reload automations")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
