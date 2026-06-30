#!/usr/bin/env python3
"""Добавить Teckin TC100 в HA через интеграцию Generic Camera (config flow)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]

CAMERA_IP = os.environ.get("TECKIN_IP", "192.168.1.84")
CAMERA_NAME = os.environ.get("TECKIN_NAME", "Teckin TC100")
CAMERA_USER = os.environ.get("TECKIN_USER", "root")
CAMERA_PASS = os.environ.get("TECKIN_PASS", "pass")
ENTITY_ID = os.environ.get("TECKIN_ENTITY", "camera.teckin_tc100")

USER_PAYLOAD = {
    "stream_source": f"rtsp://{CAMERA_IP}:554/video0_unicast",
    "still_image_url": f"https://{CAMERA_IP}/cgi-bin/currentpic.cgi",
    "username": CAMERA_USER,
    "password": CAMERA_PASS,
    "advanced": {
        "framerate": 2,
        "verify_ssl": False,
        "rtsp_transport": "tcp",
        "authentication": "basic",
    },
}


def load_token() -> str:
    token = os.environ.get("HA_TOKEN", "")
    if not token and (EMPIRE_DIR / ".env").exists():
        for line in (EMPIRE_DIR / ".env").read_text().splitlines():
            if line.startswith("HA_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        print("HA_TOKEN не задан", file=sys.stderr)
        sys.exit(2)
    return token


def ha_base() -> str:
    return os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")


def api(method: str, path: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{ha_base()}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {load_token()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:2000]
        print(f"HA API {path}: {e.code} {detail}", file=sys.stderr)
        raise


def existing_entry() -> dict | None:
    states = api("GET", "/api/states")
    if ENTITY_ID in {s["entity_id"] for s in states}:
        return {"entry_id": "existing"}
    slug = CAMERA_IP.replace(".", "_")
    for s in states:
        eid = s["entity_id"]
        if eid.startswith("camera.") and slug in eid:
            return {"entry_id": "existing", "entity_id": eid}
    for e in api("GET", "/api/config/config_entries/entry"):
        if e.get("domain") != "generic":
            continue
        opts = e.get("options") or {}
        if CAMERA_IP in str(opts.get("stream_source", "")):
            return e
    return None


def add_camera() -> str:
    flow = api("POST", "/api/config/config_entries/flow", {"handler": "generic"})
    flow_id = flow["flow_id"]
    step = api("POST", f"/api/config/config_entries/flow/{flow_id}", USER_PAYLOAD)

    for _ in range(6):
        if step.get("type") == "create_entry":
            entry_id = step["result"]["entry_id"]
            print(f"Интеграция generic: {step['result'].get('title')} ({entry_id})")
            return entry_id
        if step.get("type") != "form":
            break
        fields = {x.get("name") for x in step.get("data_schema", [])}
        if "confirmed_ok" in fields:
            step = api(
                "POST",
                f"/api/config/config_entries/flow/{flow_id}",
                {"confirmed_ok": True},
            )
        else:
            step = api("POST", f"/api/config/config_entries/flow/{flow_id}", USER_PAYLOAD)

    print("Config flow не завершён:", json.dumps(step, indent=2, ensure_ascii=False)[:2000])
    sys.exit(1)


async def rename_entity(old_id: str) -> None:
    try:
        import websockets
    except ImportError:
        print(f"websockets не установлен — entity останется {old_id}")
        return

    ws_url = ha_base().replace("http", "ws", 1) + "/api/websocket"
    async with websockets.connect(ws_url, max_size=10_000_000) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": load_token()}))
        if json.loads(await ws.recv())["type"] != "auth_ok":
            return
        await ws.send(
            json.dumps(
                {
                    "id": 1,
                    "type": "config/entity_registry/update",
                    "entity_id": old_id,
                    "new_entity_id": ENTITY_ID,
                    "name": CAMERA_NAME,
                }
            )
        )
        res = json.loads(await ws.recv())
        if res.get("success"):
            print(f"Переименовано: {old_id} → {ENTITY_ID}")
        else:
            print("Не удалось переименовать:", res)


def find_camera_entity() -> str | None:
    states = api("GET", "/api/states")
    if ENTITY_ID in {s["entity_id"] for s in states}:
        return ENTITY_ID
    slug = CAMERA_IP.replace(".", "_")
    for s in states:
        eid = s["entity_id"]
        if eid.startswith("camera.") and (slug in eid or CAMERA_IP in str(s)):
            return eid
    return None


def main() -> int:
    if existing_entry():
        print(f"Уже настроено для {CAMERA_IP}")
    else:
        add_camera()

    eid = find_camera_entity()
    slug = CAMERA_IP.replace(".", "_")
    if eid and eid != ENTITY_ID and slug in eid:
        asyncio.run(rename_entity(eid))
        eid = ENTITY_ID

    if eid:
        states = api("GET", "/api/states")
        match = [s for s in states if s["entity_id"] == eid]
        if match:
            print(f"entity: {eid} state={match[0]['state']}")
        else:
            slug = CAMERA_IP.replace(".", "_")
            alt = next(
                (s for s in states if s["entity_id"].startswith("camera.") and slug in s["entity_id"]),
                None,
            )
            if alt:
                print(f"entity: {alt['entity_id']} state={alt['state']} (перезапустите HA для {ENTITY_ID})")
            else:
                print(f"Камера добавлена; entity {eid} появится после перезагрузки HA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
