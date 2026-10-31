#!/usr/bin/env python3
"""Включить еженедельный локальный бэкап HA + комнаты Tuya."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
LOCALTUYA_ENTRY = "01F1XRJS41AC54X2WPAEHVBMS1"


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def api(method: str, path: str, body: dict | None = None, timeout: int = 90):
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


async def ws_session():
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    ws = await websockets.connect(ws_url)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    if json.loads(await ws.recv()).get("type") != "auth_ok":
        raise RuntimeError("ws auth failed")
    return ws


async def call(ws, **msg):
    if not hasattr(call, "mid"):
        call.mid = 0
    call.mid += 1
    msg = dict(msg)
    msg["id"] = call.mid
    await ws.send(json.dumps(msg))
    while True:
        data = json.loads(await ws.recv())
        if data.get("id") == call.mid:
            return data


async def enable_backup(ws) -> None:
    print("==> HA automatic backup")
    result = await call(
        ws,
        type="backup/config/update",
        automatic_backups_configured=True,
        create_backup={
            "agent_ids": ["hassio.local"],
            "include_all_addons": True,
            "include_database": True,
            "include_folders": ["share", "addons/local", "ssl", "media"],
            "name": "Empire weekly",
        },
        retention={"copies": 4, "days": None},
        schedule={"recurrence": "custom_days", "days": ["sun"], "time": "04:00"},
    )
    print("  update:", "ok" if result.get("success") else result)
    info = (await call(ws, type="backup/config/info")).get("result", {}).get("config", {})
    print("  schedule:", json.dumps(info.get("schedule"), ensure_ascii=False))
    print("  next:", info.get("next_automatic_backup"))
    print("  agents:", info.get("create_backup", {}).get("agent_ids"))


async def assign_tuya_areas(ws) -> None:
    areas = {a["name"]: a["area_id"] for a in (await call(ws, type="config/area_registry/list"))["result"]}
    mapping = {
        "switch.spalnya_svet": ("Спальня родителей", "Спальня свет один"),
        "switch.spalnya_svet_2": ("Спальня родителей", "Спальня свет два"),
        "switch.kuhnya_chainik": ("Кухня", "Розетка"),
        "switch.balkon_multivarka": ("Балкон", "Мультиварка"),
        "sensor.srw_th01_balkon_balkon_tdeg_raw": ("Балкон", None),
        "sensor.srw_th01_balkon_balkon_vlazhn_raw": ("Балкон", None),
        "sensor.srw_th01_balkon_balkon_batareia_raw": ("Балкон", None),
        "sensor.balkon_temperatura": ("Балкон", "Балкон температура"),
        "sensor.balkon_vlazhnost": ("Балкон", "Балкон влажность"),
        "camera.teckin_tc100": ("Кухня", "Кухня"),
        "camera.teckin_tc100_2": ("Детская", "Детская"),
    }
    print("==> areas for tuya/climate")
    for eid, (room, name) in mapping.items():
        aid = areas.get(room)
        payload = {"type": "config/entity_registry/update", "entity_id": eid, "area_id": aid}
        if name:
            payload["name"] = name
        result = await call(ws, **payload)
        print(f"  {eid}: {'ok' if result.get('success') else result}")

    devices = (await call(ws, type="config/device_registry/list"))["result"]
    wanted = {
        "W602 Спальня": "Спальня родителей",
        "SRW-TH01 Балкон": "Балкон",
        "Smart plug Балкон": "Балкон",
        "Wifi Plug Кухня": "Кухня",
    }
    for device in devices:
        name = device.get("name_by_user") or device.get("name") or ""
        if name in wanted:
            result = await call(
                ws,
                type="config/device_registry/update",
                device_id=device["id"],
                area_id=areas[wanted[name]],
            )
            print(f"  device {name}: {'ok' if result.get('success') else result}")


def ping_from_ha(hosts: list[str]) -> None:
    host = env("HA_SSH", "root@100.80.133.85")
    port = env("HA_SSH_PORT", "22222")
    key = env("HA_SSH_KEY", str(Path.home() / ".ssh/id_ed25519"))
    cmd = " ; ".join(f"ping -c 1 -W 1 {h} >/dev/null && echo OK {h} || echo FAIL {h}" for h in hosts)
    out = subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-p", port, "-i", key, host, cmd],
        text=True,
    )
    print("==> ping Tuya/LAN")
    print(out.strip())


def probe_srw() -> None:
    print("==> balkon SRW discover")
    for svc in (
        "shell_command/balkon_srw_discover",
        "shell_command/balkon_srw_probe",
    ):
        try:
            api("POST", f"/api/services/{svc}", {})
            print(f"  {svc}: ok")
        except Exception as exc:
            print(f"  {svc}: {exc}")
    time.sleep(12)
    try:
        api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": LOCALTUYA_ENTRY})
        print("  localtuya reload: ok")
    except Exception as exc:
        print("  localtuya reload:", exc)
    time.sleep(6)
    for eid in (
        "sensor.balkon_temperatura",
        "sensor.srw_th01_balkon_balkon_tdeg_raw",
        "switch.spalnya_svet",
        "switch.spalnya_svet_2",
        "switch.kuhnya_chainik",
        "switch.balkon_multivarka",
        "light.hobeian_zg_301z",
        "light.empire_tualet_svet",
        "sensor.sber_th_temperatura",
        "sensor.spalnya_temperatura",
    ):
        try:
            state = api("GET", f"/api/states/{eid}")["state"]
        except Exception:
            state = "missing"
        print(f"  {eid}: {state}")


async def main() -> int:
    load_env()
    ping_from_ha(["192.168.1.143", "192.168.1.51", "192.168.1.40", "192.168.1.123", "192.168.1.56", "192.168.1.119"])
    ws = await ws_session()
    try:
        await enable_backup(ws)
        await assign_tuya_areas(ws)
    finally:
        await ws.close()
    probe_srw()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
