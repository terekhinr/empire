#!/usr/bin/env python3
"""Туалет: настройка mmWave + ZHA reconfigure при залипании."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.request

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

MMWAVE_IEEE = "a4:c1:38:64:a8:6e:7a:4d"


def env(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    p = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def api(method: str, path: str, body: dict | None = None):
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    if not token:
        sys.exit("HA_TOKEN не задан")
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def set_num(eid: str, value: float) -> None:
    api("POST", "/api/services/number/set_value", {"entity_id": eid, "value": value})
    print(f"set {eid} = {value}")


async def zha_reconfigure(ieee: str) -> None:
    if websockets is None:
        print("websockets не установлен — пропуск ZHA reconfigure")
        return
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            sys.exit("HA websocket auth failed")
        await ws.send(json.dumps({"id": 1, "type": "zha/devices/reconfigure", "ieee": ieee}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                break
            if msg.get("type") == "event" and msg.get("event", {}).get("type") == "zha_channel_cfg_done":
                print("ZHA reconfigure: done")
    time.sleep(12)


def main() -> None:
    set_num("number.tze204_qasjif9e_ts0601_maksimalnyi_diapazon", 3.75)
    set_num("number.tze204_qasjif9e_ts0601_chuvstvitelnost_k_dvizheniiu", 8)
    set_num("number.tze204_qasjif9e_ts0601_minimalnyi_diapazon", 0)
    set_num("number.tze204_qasjif9e_ts0601_vremia_zatukhaniia", 5)
    time.sleep(3)

    occ = api("GET", "/api/states/binary_sensor.tze204_qasjif9e_ts0601")["state"]
    print(f"occupancy before reconfigure: {occ}")
    if occ == "on":
        print("occupancy stuck on — ZHA reconfigure…")
        asyncio.run(zha_reconfigure(MMWAVE_IEEE))

    occ = api("GET", "/api/states/binary_sensor.tze204_qasjif9e_ts0601")["state"]
    dist = api("GET", "/api/states/sensor.tze204_qasjif9e_ts0601_rasstoianie_do_tseli")["state"]
    print(f"occupancy: {occ}, distance: {dist}")


if __name__ == "__main__":
    main()
