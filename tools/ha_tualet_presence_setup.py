#!/usr/bin/env python3
"""Туалет: SONOFF SNZB-06P → area tualet + автосвет."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]
IEEE = "8c:73:da:ff:fe:f2:bd:92"
PRESENCE = "binary_sensor.sonoff_snzb_06p_3"
LIGHT = "light.empire_tualet_svet"
AREA = "tualet"


def load_env() -> None:
    p = EMPIRE_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def api(method: str, path: str, body: dict | None = None):
    token = os.environ.get("HA_TOKEN", "")
    base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


async def ws_call(msg: dict) -> dict:
    import websockets

    base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    msg_id = msg.get("id", 1)
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("auth failed")
        await ws.send(json.dumps(msg))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == msg_id:
                return r


async def assign_area() -> None:
    dr = await ws_call({"id": 10, "type": "config/device_registry/list"})
    device_id = None
    for dev in dr.get("result", []):
        ids = str(dev.get("identifiers", ""))
        if IEEE.replace(":", "").lower() in ids.lower() or IEEE in ids:
            device_id = dev.get("id")
            break
    if not device_id:
        print("device not found in registry")
        return

    upd = await ws_call({
        "id": 11,
        "type": "config/device_registry/update",
        "device_id": device_id,
        "area_id": AREA,
        "name_by_user": "Туалет присутствие",
    })
    print("device area:", upd.get("success", upd.get("error")))

    er = await ws_call({"id": 20, "type": "config/entity_registry/list"})
    for ent in er.get("result", []):
        eid = ent.get("entity_id", "")
        if eid == PRESENCE or (eid.startswith("binary_sensor.sonoff_snzb_06p_3")):
            await ws_call({
                "id": 21,
                "type": "config/entity_registry/update",
                "entity_id": eid,
                "area_id": AREA,
                "name": "Присутствие",
            })
            print("entity", eid, "→ tualet")


def main() -> int:
    load_env()
    if not os.environ.get("HA_TOKEN"):
        sys.exit("HA_TOKEN не задан")

    print("==> area + name")
    asyncio.run(assign_area())

    print("==> sensitivity Low + timeout 10s (attr 32)")
    try:
        api("POST", "/api/services/select/select_option", {
            "entity_id": "select.tualet_tualet_prisutstvie_chuvstvitelnost_obnaruzheniia",
            "option": "Low",
        })
    except Exception:
        pass
    api("POST", "/api/services/zha/set_zigbee_cluster_attribute", {
        "ieee": IEEE,
        "endpoint_id": 1,
        "cluster_id": 1030,
        "cluster_type": "in",
        "attribute": 34,
        "value": 1,
    })
    # ultrasonic_o_to_u_delay = 0x0020 = 32 (НЕ 33)
    api("POST", "/api/services/zha/set_zigbee_cluster_attribute", {
        "ieee": IEEE,
        "endpoint_id": 1,
        "cluster_id": 1030,
        "cluster_type": "in",
        "attribute": 32,
        "value": 10,
    })

    api("POST", "/api/services/automation/reload", {})
    print("==> states")
    print(PRESENCE, api("GET", f"/api/states/{PRESENCE}")["state"])
    print(LIGHT, api("GET", f"/api/states/{LIGHT}")["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
