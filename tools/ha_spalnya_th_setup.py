#!/usr/bin/env python3
"""Спальня _TZE284_hodyryli: ZHA reconfigure / rejoin + reload templates."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

IEEE = "a4:c1:38:77:2a:ba:93:d0"
MANUFACTURER = "_TZE284_hodyryli"
MODEL = "TS0601"
AREA = "spalnia_roditelei"
DEVICE_NAME = "Спальня T/H"
RAW_ENTITIES = (
    "sensor.spalnia_roditelei_tze284_hodyryli_ts0601_temperatura",
    "sensor.spalnia_roditelei_tze284_hodyryli_ts0601_vneshniaia_temperatura",
    "sensor.spalnia_roditelei_tze284_hodyryli_ts0601_vlazhnost",
    "sensor.spalnia_roditelei_tze284_hodyryli_ts0601_battery",
)
TEMPLATE_ENTITIES = (
    "sensor.spalnya_temperatura",
    "sensor.spalnya_temperatura_ulica",
    "sensor.spalnya_vlazhnost",
    "sensor.spalnya_batareia",
)


def load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    dot = root / ".env"
    if dot.is_file():
        for line in dot.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def api(method: str, path: str, body: dict | None = None) -> dict | list | None:
    base = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not base or not token:
        sys.exit("HA_URL и HA_TOKEN обязательны")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


async def zha_reconfigure() -> bool:
    try:
        import websockets
    except ImportError:
        print("websockets не установлен — пропуск reconfigure")
        return False
    base = os.environ["HA_URL"].rstrip("/")
    token = os.environ["HA_TOKEN"]
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            return False
        await ws.send(json.dumps({"id": 1, "type": "zha/devices/reconfigure", "ieee": IEEE}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if msg.get("success"):
                    print("ZHA reconfigure: ok")
                    return True
                print("ZHA reconfigure:", msg.get("error", msg))
                return False


def rename_device() -> None:
    try:
        import websockets
    except ImportError:
        return

    async def _run() -> None:
        base = os.environ["HA_URL"].rstrip("/")
        token = os.environ["HA_TOKEN"]
        ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
        async with websockets.connect(ws_url) as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "auth", "access_token": token}))
            await ws.recv()
            await ws.send(json.dumps({"id": 2, "type": "config/device_registry/list"}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") != 2:
                    continue
                dev = next(
                    (
                        d
                        for d in msg.get("result", [])
                        if d.get("manufacturer") == MANUFACTURER and d.get("model") == MODEL
                    ),
                    None,
                )
                if not dev:
                    return
                await ws.send(
                    json.dumps(
                        {
                            "id": 3,
                            "type": "config/device_registry/update",
                            "device_id": dev["id"],
                            "name_by_user": DEVICE_NAME,
                            "area_id": AREA,
                        }
                    )
                )
                while True:
                    upd = json.loads(await ws.recv())
                    if upd.get("id") == 3:
                        print(f"device renamed → {DEVICE_NAME}, area {AREA}")
                        return

    asyncio.run(_run())


def zha_rejoin() -> None:
    """Удалить устройство и открыть permit — нужно нажать кнопку на датчике."""
    try:
        api("POST", "/api/services/zha/remove", {"ieee": IEEE})
        print("zha/remove: ok")
    except urllib.error.HTTPError as exc:
        print("zha/remove:", exc)
    try:
        api("POST", "/api/services/zha/permit", {"duration": 120})
        print("zha/permit 120 с: ok — нажмите кнопку на датчике «Спальня T/H»")
    except urllib.error.HTTPError as exc:
        print("zha/permit:", exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Спальня T/H ZHA setup")
    parser.add_argument(
        "--rejoin",
        action="store_true",
        help="удалить из ZHA и открыть permit 120 с (после установки quirk)",
    )
    args = parser.parse_args()

    load_env()
    try:
        api("POST", "/api/services/template/reload", {})
        print("template/reload: ok")
    except urllib.error.HTTPError as exc:
        print("template/reload:", exc)

    if args.rejoin:
        zha_rejoin()
    else:
        asyncio.run(zha_reconfigure())
    rename_device()

    print("\n=== Сущности ===")
    states = {s["entity_id"]: s for s in api("GET", "/api/states")}
    for eid in RAW_ENTITIES + TEMPLATE_ENTITIES:
        st = states.get(eid)
        if st:
            print(f"  OK  {eid} = {st['state']}")
        else:
            print(f"  --- {eid} (нет)")

    missing = [e for e in RAW_ENTITIES if e not in states]
    if missing:
        print("\nЕсли raw-сущностей нет: ZHA → «Спальня T/H» → ⋮ → Перенастроить")
        print("или удалить и снова добавить (permit 60 с, кнопка на датчике).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
