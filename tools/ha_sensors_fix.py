#!/usr/bin/env python3
"""Ванная: Sonoff High. Туалет: mmWave max + ZHA reconfigure."""
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
    websockets = None

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
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


async def zha_reconfigure(ieee: str) -> None:
    if websockets is None:
        return
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            return
        await ws.send(json.dumps({"id": 1, "type": "zha/devices/reconfigure", "ieee": ieee}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                break
            if msg.get("type") == "event":
                print("ZHA:", msg.get("event", {}).get("type"))
    time.sleep(10)


def main() -> None:
    api("POST", "/api/services/select/select_option", {
        "entity_id": "select.sonoff_snzb_06p_chuvstvitelnost_obnaruzheniia",
        "option": "High",
    })
    print("sonoff sensitivity → High")

    for eid, val in {
        "number.tualet_tze204_qasjif9e_ts0601_chuvstvitelnost_radara": 9,
        "number.tze204_qasjif9e_ts0601_chuvstvitelnost_k_dvizheniiu": 10,
        "number.tze204_qasjif9e_ts0601_maksimalnyi_diapazon": 3.75,
        "number.tze204_qasjif9e_ts0601_minimalnyi_diapazon": 0,
        "number.tze204_qasjif9e_ts0601_zaderzhka_obnaruzheniia": 1,
        "number.tze204_qasjif9e_ts0601_vremia_zatukhaniia": 5,
    }.items():
        try:
            api("POST", "/api/services/number/set_value", {"entity_id": eid, "value": val})
            print(f"set {eid} = {val}")
        except Exception as ex:
            if "404" not in str(ex):
                print(f"skip {eid}: {ex}")

    print("ZHA reconfigure mmWave…")
    asyncio.run(zha_reconfigure(MMWAVE_IEEE))

    for eid in ("binary_sensor.sonoff_snzb_06p", "binary_sensor.tze204_qasjif9e_ts0601"):
        try:
            print(eid, api("GET", f"/api/states/{eid}")["state"])
        except Exception:
            print(eid, "missing")


if __name__ == "__main__":
    main()
