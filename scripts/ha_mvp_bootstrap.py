#!/usr/bin/env python3
"""Создание зон (areas) в HA через WebSocket API."""
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

AREAS = [
    ("gostevaya", "Гостевая"),
    ("kuhnya", "Кухня"),
    ("spalnya_roditeley", "Спальня родителей"),
    ("komnata_maksa", "Комната Макса"),
    ("komnata_semiona", "Комната Семена"),
    ("prihozhaya", "Прихожая"),
    ("koridor", "Коридор"),
    ("vannaya", "Ванная"),
    ("balkon", "Балкон"),
    ("tualet", "Туалет"),
]


async def main() -> int:
    base = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not base or not token:
        print("HA_URL и HA_TOKEN в окружении", file=sys.stderr)
        return 1

    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        hello = json.loads(await ws.recv())
        if hello.get("type") != "auth_required":
            print("unexpected:", hello)
            return 1

        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print("auth failed:", auth)
            return 1

        await ws.send(json.dumps({"id": msg_id, "type": "config/area_registry/list"}))
        msg_id += 1
        existing: set[str] = set()
        while True:
            raw = json.loads(await ws.recv())
            if raw.get("id") == msg_id - 1 and raw.get("success"):
                for a in raw.get("result", []):
                    existing.add(a.get("name", ""))
                break

        created = 0
        for _slug, name in AREAS:
            if name in existing:
                print(f"skip exists: {name}")
                continue
            await ws.send(
                json.dumps(
                    {
                        "id": msg_id,
                        "type": "config/area_registry/create",
                        "name": name,
                    }
                )
            )
            msg_id += 1
            res = json.loads(await ws.recv())
            if res.get("success"):
                print(f"created: {name}")
                created += 1
            else:
                print(f"fail {name}:", res)

        print(f"done, created {created} areas")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
