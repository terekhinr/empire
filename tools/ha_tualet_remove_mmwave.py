#!/usr/bin/env python3
"""Удалить снятый mmWave туалета и мусорные entity из HA (без re-pair)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.request

IEEE = "a4:c1:38:64:a8:6e:7a:4d"

try:
    import websockets
except ImportError:
    sys.exit("pip install websockets")


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
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


async def ws_call(ws, msg_id: int, msg_type: str, **kwargs) -> dict:
    await ws.send(json.dumps({"id": msg_id, "type": msg_type, **kwargs}))
    while True:
        r = json.loads(await ws.recv())
        if r.get("id") == msg_id:
            if not r.get("success", True):
                raise RuntimeError(r.get("error", r))
            return r


def stale_entity(eid: str) -> bool:
    keys = ("qasjif9e", "tualet_tze204", "empire_tualet_presence")
    return any(k in eid for k in keys)


def stale_automation(eid: str) -> bool:
    return eid in {
        "automation.tualet_min_dalnost_mmwave_pri_starte",
        "automation.tualet_net_prisutstviia_svet_vykl",
        "automation.tualet_prisutstvie_svet_vkl",
    }


async def main() -> None:
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"

    print("1) zha/remove", IEEE)
    try:
        api("POST", "/api/services/zha/remove", {"ieee": IEEE})
    except Exception as ex:
        print("   (zha/remove:", ex, ")")
    time.sleep(2)

    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            sys.exit("auth failed")

        mid = 1
        dr = await ws_call(ws, mid, "config/device_registry/list")
        mid += 1
        for dev in dr.get("result", []):
            name = str(dev.get("name", "")).lower()
            ids = json.dumps(dev.get("identifiers", [])).lower()
            if IEEE in ids or "qasjif9e" in name or "qasjif9e" in ids:
                print("2) remove device", dev.get("name"), dev.get("id"))
                await ws_call(ws, mid, "config/device_registry/remove", device_id=dev.get("id"))
                mid += 1

        er = await ws_call(ws, mid, "config/entity_registry/list")
        mid += 1
        removed = 0
        for ent in er.get("result", []):
            eid = ent.get("entity_id", "")
            if stale_entity(eid) or stale_automation(eid):
                print("3) remove entity", eid)
                await ws_call(ws, mid, "config/entity_registry/remove", entity_id=eid)
                mid += 1
                removed += 1
        print(f"   removed {removed} entities")

    print("4) reload automations")
    api("POST", "/api/services/automation/reload", {})


if __name__ == "__main__":
    asyncio.run(main())
