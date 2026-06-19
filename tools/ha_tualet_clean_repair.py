#!/usr/bin/env python3
"""Туалет mmWave: удалить устройство + мусорные entity + permit для чистого спаривания."""
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


async def ws_call(msg: dict) -> dict:
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
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


async def main() -> None:
    print("1) remove ZHA device", IEEE)
    api("POST", "/api/services/zha/remove", {"ieee": IEEE})
    time.sleep(3)

    print("2) remove device registry entry")
    dr = await ws_call({"id": 10, "type": "config/device_registry/list"})
    for dev in dr.get("result", []):
        if dev.get("identifiers") and any(IEEE.replace(":", "").lower() in str(i).lower() or IEEE in str(i) for i in dev.get("identifiers", [])):
            print("   del device", dev.get("id"), dev.get("name"))
            await ws_call({"id": 11, "type": "config/device_registry/remove", "device_id": dev.get("id")})
        elif "qasjif9e" in str(dev.get("name", "")).lower() or "qasjif9e" in str(dev.get("model", "")).lower():
            print("   del device", dev.get("id"), dev.get("name"))
            await ws_call({"id": 12, "type": "config/device_registry/remove", "device_id": dev.get("id")})

    print("3) remove stale entity registry entries")
    er = await ws_call({"id": 10, "type": "config/entity_registry/list"})
    removed = 0
    for ent in er.get("result", []):
        eid = ent.get("entity_id", "")
        if "qasjif9e" in eid or "tualet_tze204" in eid:
            print("   del", eid)
            await ws_call({
                "id": 20 + removed,
                "type": "config/entity_registry/remove",
                "entity_id": eid,
            })
            removed += 1
    print(f"   removed {removed} entities")

    print("4) open permit 180s — НАЖМИ КНОПКУ НА ДАТЧИКЕ 5-10 сек")
    api("POST", "/api/services/zha/permit", {"duration": 180})

    print("5) waiting for device (90s)…")
    for i in range(18):
        time.sleep(5)
        try:
            r = await ws_call({"id": 100, "type": "zha/devices"})
            for d in r.get("result", []):
                if d.get("ieee") == IEEE or "qasjif9e" in json.dumps(d):
                    print("   JOINED:", d.get("ieee"), "quirk", d.get("quirk_class"))
                    ents = [e.get("entity_id") for e in d.get("entities", [])]
                    print("   entities:", ", ".join(sorted(ents)))
                    return
        except Exception as ex:
            print("   poll err", ex)
        print(f"   …{(i+1)*5}s")

    print("   device not seen yet — нажми кнопку на датчике и подожди")


if __name__ == "__main__":
    asyncio.run(main())
