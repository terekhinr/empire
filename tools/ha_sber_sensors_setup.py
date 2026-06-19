#!/usr/bin/env python3
"""Sber Zigbee: ZHA permit join, поиск SBDV-00079 / SBDV-00030, имена и области.

  cd /root/projects/empire && set -a && source .env && set +a
  python3 tools/ha_sber_sensors_setup.py permit          # 240 с pairing
  python3 tools/ha_sber_sensors_setup.py configure       # после сброса датчиков
  python3 tools/ha_sber_sensors_setup.py wait            # permit + ждать до 5 мин
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

try:
    import websockets
except ImportError:
    websockets = None

SBER_MODELS = {
    "SBDV-00079": {
        "name": "Sber T/H",
        "area_env": "SBER_TH_AREA",
        "area_default": "Кухня",
        "entities": {
            "temperature": "sensor.sber_th_temperatura",
            "humidity": "sensor.sber_th_vlazhnost",
            "battery": "sensor.sber_th_batareia",
        },
    },
    "SBDV-00030": {
        "name": "Sber открытие",
        "area_env": "SBER_DOOR_AREA",
        "area_default": "Прихожая",
        "entities": {
            "opening": "binary_sensor.sber_otkrytie",
            "battery": "sensor.sber_otkrytie_batareia",
        },
    },
}

# Tuya-отпечатки на случай, если ZHA покажет manufacturer до quirk
TUYA_FP = {
    ("_TZ3000_zfirri2d", "TS0201"): "SBDV-00079",
    ("_TYZB01_epni2jgy", "TS0203"): "SBDV-00030",
}


def env(name: str, default: str = "") -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    p = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return default


def api(method: str, path: str, body: dict | None = None):
    base = env("HA_URL", "http://127.0.0.1:8123").rstrip("/")
    token = env("HA_TOKEN")
    if not token:
        sys.exit("HA_TOKEN не задан")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def telegram(msg: str) -> None:
    try:
        api("POST", "/api/services/rest_command/empire_telegram", {"message": msg})
    except Exception as ex:
        print(f"telegram skip: {ex}")


def permit(duration: int = 240) -> None:
    duration = min(max(int(duration), 1), 254)
    api("POST", "/api/services/zha/permit", {"duration": duration})
    print(f"ZHA permit join: {duration} с")
    telegram(
        f"HA: ZHA pairing {duration} с.\n"
        "Сбросьте датчики Sber (кнопка → мигание) рядом с координатором."
    )


def resolve_model(dev: dict) -> str | None:
    model = (dev.get("model") or "").strip()
    if model in SBER_MODELS:
        return model
    mfr = (dev.get("manufacturer") or "").strip()
    key = (mfr, model)
    if key in TUYA_FP:
        return TUYA_FP[key]
    if mfr.lower() == "sber" and model:
        return model if model in SBER_MODELS else None
    return None


async def ws_session():
    if websockets is None:
        sys.exit("pip install websockets")
    base = env("HA_URL", "http://127.0.0.1:8123").rstrip("/")
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    ws = await websockets.connect(ws_url)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    if json.loads(await ws.recv()).get("type") != "auth_ok":
        await ws.close()
        sys.exit("HA websocket auth failed")
    return ws


async def ws_call(ws, mid: int, msg: dict) -> tuple[int, dict]:
    await ws.send(json.dumps({"id": mid, **msg}))
    while True:
        raw = json.loads(await ws.recv())
        if raw.get("id") == mid:
            return mid + 1, raw


async def load_registry(ws):
    mid = 1
    mid, areas_raw = await ws_call(ws, mid, {"type": "config/area_registry/list"})
    mid, devs_raw = await ws_call(ws, mid, {"type": "config/device_registry/list"})
    mid, ents_raw = await ws_call(ws, mid, {"type": "config/entity_registry/list"})
    mid, zha_raw = await ws_call(ws, mid, {"type": "zha/devices"})
    return mid, areas_raw["result"], devs_raw["result"], ents_raw["result"], zha_raw["result"]


def area_id_by_name(areas: list, name: str) -> str | None:
    if not name:
        return None
    for a in areas:
        if a.get("name") == name:
            return a["area_id"]
    return None


def entity_device_class(ent: dict) -> str:
    return (ent.get("original_device_class") or ent.get("device_class") or "").lower()


async def configure_devices(ws) -> int:
    mid, areas, devices, entities, zha_devices = await load_registry(ws)
    configured = 0

    for zd in zha_devices:
        model_key = resolve_model(zd)
        if not model_key:
            continue
        spec = SBER_MODELS[model_key]
        dev_id = zd.get("device_reg_id")
        if not dev_id:
            continue

        area_name = env(spec["area_env"], spec["area_default"])
        area_id = area_id_by_name(areas, area_name)
        mid, upd = await ws_call(
            ws,
            mid,
            {
                "type": "config/device_registry/update",
                "device_id": dev_id,
                "name_by_user": spec["name"],
                **({"area_id": area_id} if area_id else {}),
            },
        )
        if upd.get("success"):
            print(f"✓ {model_key} → «{spec['name']}»" + (f", область «{area_name}»" if area_id else ""))
            configured += 1
        else:
            print(f"! device_registry {model_key}: {upd.get('error')}")

        dev_ents = [e for e in entities if e.get("device_id") == dev_id]
        zha_ents = {e.get("entity_id"): e for e in zd.get("entities", []) if e.get("entity_id")}

        for ent in dev_ents:
            eid = ent["entity_id"]
            domain, slug = eid.split(".", 1)
            target = None
            dc = entity_device_class(ent)
            if model_key == "SBDV-00079":
                if dc == "temperature" or "temperatura" in slug:
                    target = spec["entities"]["temperature"]
                elif dc == "humidity" or "vlazhnost" in slug:
                    target = spec["entities"]["humidity"]
                elif dc == "battery" or "batareia" in slug:
                    target = spec["entities"]["battery"]
            elif model_key == "SBDV-00030":
                if domain == "binary_sensor" and dc in ("opening", "door", "window", ""):
                    target = spec["entities"]["opening"]
                elif dc == "battery" or "batareia" in slug or slug.endswith("_battery"):
                    target = spec["entities"]["battery"]
                elif "otkrytie" in slug or "contact" in slug:
                    target = spec["entities"]["opening"]

            if not target or target == eid:
                continue
            mid, eupd = await ws_call(
                ws,
                mid,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": eid,
                    "new_entity_id": target,
                },
            )
            if eupd.get("success"):
                print(f"  entity {eid} → {target}")
            else:
                print(f"  ! entity {eid}: {eupd.get('error')}")

        for ze in zha_ents.values():
            print(f"  ZHA: {ze.get('entity_id')} ({ze.get('name', '')})")

    if not configured:
        print("Sber-датчики в ZHA не найдены. Сначала: permit → сброс на датчике (кнопка, мигание).")
        return 1
    telegram(f"HA: настроено Sber-датчиков: {configured}")
    return 0


async def wait_for_pair(permit_sec: int, timeout_sec: int) -> int:
    permit(permit_sec)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        ws = await ws_session()
        try:
            _, _, _, _, zha = await load_registry(ws)
            found = [resolve_model(d) for d in zha if resolve_model(d)]
            if len(found) >= 2:
                print(f"Найдено моделей: {found}")
                rc = await configure_devices(ws)
                return rc
            if found:
                print(f"Пока только: {found} — ждём второй датчик…")
        finally:
            await ws.close()
        await asyncio.sleep(15)
    print("Таймаут. Запустите configure после сброса датчиков.")
    return 1


async def async_main(args: argparse.Namespace) -> int:
    if args.cmd == "permit":
        permit(args.duration)
        return 0
    ws = await ws_session()
    try:
        if args.cmd == "configure":
            return await configure_devices(ws)
    finally:
        await ws.close()
    if args.cmd == "wait":
        return await wait_for_pair(args.duration, args.timeout)
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("permit", help="ZHA permit join")
    sp.add_argument("--duration", type=int, default=300)
    sub.add_parser("configure", help="Имена и entity_id после pairing")
    sw = sub.add_parser("wait", help="permit + ждать датчики")
    sw.add_argument("--duration", type=int, default=300)
    sw.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
