#!/usr/bin/env python3
"""Настроить Teckin в HA: IP, имя, область (комната).

  TECKIN2_IP=192.168.1.84 venv/bin/python3 tools/ha_teckin_configure.py --slot 2 \\
    --name "Комната Макса" --area "Комната Макса"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

EMPIRE_DIR = Path(__file__).resolve().parents[1]

SLOTS = {
    "1": {
        "entity": "camera.teckin_tc100",
        "default_ip": "192.168.1.34",
        "env_ip": "TECKIN_IP",
        "entry_hint": "01KVWABNDDHAQ09RB9A3HSV9ZY",
    },
    "2": {
        "entity": "camera.teckin_tc100_2",
        "default_ip": "192.168.1.84",
        "env_ip": "TECKIN2_IP",
        "entry_hint": "01KVWBAEFZTVY274BA6HBCRNQE",
    },
}


def load_env() -> None:
    env_path = EMPIRE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ha_base() -> str:
    return os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")


def ha_token() -> str:
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        sys.exit("HA_TOKEN не задан (.env)")
    return token


def api(method: str, path: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{ha_base()}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {ha_token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def build_options(ip: str, password: str = "pass") -> dict:
    return {
        "stream_source": f"rtsp://{ip}:554/video0_unicast",
        "still_image_url": f"https://{ip}/cgi-bin/currentpic.cgi",
        "username": "root",
        "password": password,
        "content_type": "image/jpeg",
        "advanced": {
            "authentication": "basic",
            "framerate": 2,
            "rtsp_transport": "tcp",
            "verify_ssl": False,
        },
    }


async def ws_call(ws, msg_id: int, payload: dict) -> dict:
    payload = dict(payload)
    payload["id"] = msg_id
    await ws.send(json.dumps(payload))
    while True:
        raw = json.loads(await ws.recv())
        if raw.get("id") == msg_id:
            return raw


async def configure(slot: str, ip: str, name: str | None, area: str | None) -> None:
    if websockets is None:
        sys.exit("pip install websockets")

    meta = SLOTS[slot]
    pwd = os.environ.get("TECKIN_PASS", "pass")
    entry_id = None
    for e in api("GET", "/api/config/config_entries/entry"):
        if e.get("domain") != "generic":
            continue
        if e.get("entry_id") == meta["entry_hint"]:
            entry_id = e["entry_id"]
            break
        opts = e.get("options") or {}
        if ip in str(opts.get("stream_source", "")):
            entry_id = e["entry_id"]
            break
    if not entry_id:
        sys.exit(f"generic entry для slot {slot} не найден — сначала ha_teckin_tc100_setup.py")

    # config_entries/update не принимает полный options — правим storage напрямую
    import subprocess
    import tempfile

    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    tmp = Path(tempfile.gettempdir()) / "ha_ce_teckin_slot.json"
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port,
         f"{ha_host}:/config/.storage/core.config_entries", str(tmp)],
        check=True,
    )
    ce = json.loads(tmp.read_text())
    for e in ce["data"]["entries"]:
        if e.get("entry_id") != entry_id:
            continue
        e["options"] = build_options(ip, pwd)
        e["title"] = ip.replace(".", "_")
        print(f"✓ generic entry {entry_id} → {ip}")
        break
    tmp.write_text(json.dumps(ce, indent=2))
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port,
         str(tmp), f"{ha_host}:/config/.storage/core.config_entries"],
        check=True,
    )

    ws_url = ha_base().replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": ha_token()}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("websocket auth failed")

        mid = 1
        area_id = None
        if area:
            mid += 1
            areas = (await ws_call(ws, mid, {"type": "config/area_registry/list"})).get("result", [])
            area_id = next((a["area_id"] for a in areas if a.get("name") == area), None)
            if not area_id:
                print(f"  WARN: область «{area}» не найдена")
            else:
                print(f"✓ область «{area}» → {area_id}")

        entity_id = meta["entity"]
        mid += 1
        ents = (await ws_call(ws, mid, {"type": "config/entity_registry/list"})).get("result", [])
        ent = next((e for e in ents if e.get("entity_id") == entity_id), None)
        if not ent and ip:
            slug = ip.replace(".", "_")
            ent = next((e for e in ents if slug in e.get("entity_id", "")), None)
            if ent:
                entity_id = ent["entity_id"]

        if ent and (name or area_id):
            payload: dict = {"type": "config/entity_registry/update", "entity_id": entity_id}
            if name:
                payload["name"] = name
            if area_id:
                payload["area_id"] = area_id
            mid += 1
            r = await ws_call(ws, mid, payload)
            if not r.get("success", True):
                raise RuntimeError(r.get("error", r))
            print(f"✓ entity {entity_id}: name={name!r}, area={area!r}")

        if ent and area_id and ent.get("device_id"):
            mid += 1
            r = await ws_call(
                ws,
                mid,
                {
                    "type": "config/device_registry/update",
                    "device_id": ent["device_id"],
                    "area_id": area_id,
                    "name_by_user": name,
                },
            )
            if r.get("success"):
                print(f"✓ device {ent['device_id'][:8]}… → область «{area}»")

    api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": entry_id})

    # reload не подхватывает правки .storage — нужен restart core
    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    import subprocess
    print("  перезапуск HA core (подхват IP из storage)…")
    subprocess.run(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, ha_host, "ha core restart"],
        check=True,
        timeout=180,
    )
    state = api("GET", f"/api/states/{meta['entity']}")
    print(f"✓ {meta['entity']} state={state.get('state')} name={state.get('attributes', {}).get('friendly_name')}")


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=("1", "2"), default="2")
    parser.add_argument("--ip", help="IP камеры (по умолчанию из TECKIN2_IP / default)")
    parser.add_argument("--name", help="Отображаемое имя entity")
    parser.add_argument("--area", help="Область HA (комната)")
    args = parser.parse_args()

    meta = SLOTS[args.slot]
    ip = args.ip or os.environ.get(meta["env_ip"], meta["default_ip"])
    asyncio.run(configure(args.slot, ip, args.name, args.area))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
