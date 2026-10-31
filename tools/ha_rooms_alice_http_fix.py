#!/usr/bin/env python3
"""Разнести устройства по комнатам HA + перезалить фильтр Алисы."""
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
ENTRY_ID = "01KRZWQPJBMBDSE4GGXWKW039M"

ASSIGN = {
    "camera.teckin_tc100": "Кухня",
    "camera.teckin_tc100_2": "Детская",
    "camera.ezviz_prihozhaya": "Прихожая",
    "camera.ezviz_podezd": "Прихожая",
    "binary_sensor.ezviz_prihozhaya_motion_alarm": "Прихожая",
    "binary_sensor.ezviz_podezd_motion_alarm": "Прихожая",
    "sensor.balkon_temperatura": "Балкон",
    "sensor.balkon_vlazhnost": "Балкон",
    "sensor.balkon_batareia": "Балкон",
    "sensor.srw_th01_balkon_balkon_tdeg_raw": "Балкон",
    "sensor.srw_th01_balkon_balkon_vlazhn_raw": "Балкон",
    "sensor.srw_th01_balkon_balkon_batareia_raw": "Балкон",
    "sensor.spalnya_temperatura": "Спальня родителей",
    "sensor.spalnya_vlazhnost": "Спальня родителей",
    "sensor.spalnya_batareia": "Спальня родителей",
    "sensor.spalnya_temperatura_ulica": "Спальня родителей",
    "light.empire_kuhnya_svet": "Кухня",
    "light.empire_tualet_svet": "Туалет",
    "light.empire_vannaya_svet": "Ванная",
    "light.empire_prihozhaya_svet": "Прихожая",
    "switch.basicr2_ded_sonoff_10011f1029": "Гостевая",
    "switch.basicr2_max_sonoff_10011f28d9": "Комната Семёна",
    "switch.spalnya_svet": "Спальня родителей",
    "switch.spalnya_svet_2": "Спальня родителей",
    "switch.balkon_multivarka": "Балкон",
    "binary_sensor.balkon_datchik_gaza": "Балкон",
    "binary_sensor.kukhnia_datchik_gaza_predvaritelnyi_nagrev_aktiven": "Балкон",
    "binary_sensor.kukhnia_datchik_gaza_signalizatsiia_bez_zvuka": "Балкон",
    "switch.kukhnia_datchik_gaza_samodiagnostika": "Балкон",
}

NAMES = {
    "binary_sensor.balkon_datchik_gaza": "Датчик газа",
    "sensor.balkon_batareia": "Балкон батарея",
    "camera.teckin_tc100": "Кухня",
    "camera.teckin_tc100_2": "Детская",
    "camera.ezviz_prihozhaya": "Прихожая",
    "camera.ezviz_podezd": "Подъезд",
    "switch.basicr2_ded_sonoff_10011f1029": "Свет",
    "switch.basicr2_max_sonoff_10011f28d9": "Свет",
    "binary_sensor.kukhnia_datchik_gaza_predvaritelnyi_nagrev_aktiven": "Датчик газа — нагрев",
    "binary_sensor.kukhnia_datchik_gaza_signalizatsiia_bez_zvuka": "Датчик газа — без звука",
    "switch.kukhnia_datchik_gaza_samodiagnostika": "Датчик газа — самодиагностика",
}


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


def scp(local: Path, remote: str) -> None:
    host = env("HA_SSH", "root@100.80.133.85")
    port = env("HA_SSH_PORT", "22222")
    key = env("HA_SSH_KEY", str(Path.home() / ".ssh/id_ed25519"))
    subprocess.run(
        ["scp", "-P", port, "-i", key, "-o", "BatchMode=yes", str(local), f"{host}:{remote}"],
        check=True,
        capture_output=True,
    )
    print("scp", local.name)


async def assign_areas() -> None:
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    ws = await websockets.connect(ws_url)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    if json.loads(await ws.recv()).get("type") != "auth_ok":
        raise RuntimeError("ws auth failed")
    mid = 0

    async def call(**msg):
        nonlocal mid
        mid += 1
        msg = dict(msg)
        msg["id"] = mid
        await ws.send(json.dumps(msg))
        while True:
            data = json.loads(await ws.recv())
            if data.get("id") == mid:
                return data

    areas = {a["name"]: a["area_id"] for a in (await call(type="config/area_registry/list"))["result"]}
    print("==> areas")
    for eid, room in ASSIGN.items():
        aid = areas.get(room)
        if not aid:
            print(" missing area", room)
            continue
        payload = {"type": "config/entity_registry/update", "entity_id": eid, "area_id": aid}
        if eid in NAMES:
            payload["name"] = NAMES[eid]
        result = await call(**payload)
        print(f"  {eid} → {room}: {'ok' if result.get('success') else result}")
    await ws.close()


def main() -> int:
    load_env()
    scp(ROOT / "homeassistant/yandex_smart_home.yaml", "/homeassistant/yandex_smart_home.yaml")
    scp(ROOT / "homeassistant/packages/empire_http_keenetic.yaml", "/homeassistant/packages/empire_http_keenetic.yaml")
    asyncio.run(assign_areas())
    api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": ENTRY_ID})
    time.sleep(4)
    try:
        api("POST", "/api/services/yandex_smart_home/reload", {})
    except Exception as exc:
        print("yandex reload", exc)
    time.sleep(5)
    diag = api("GET", f"/api/diagnostics/config_entry/{ENTRY_ID}") or {}
    devices = diag.get("data", {}).get("devices", {})
    print(f"YANDEX devices: {len(devices)}")
    for eid, item in sorted(devices.items()):
        if eid.startswith(("light.", "switch.", "script.svet_")):
            desc = item.get("description") or {}
            print(f"  {desc.get('room')!r:20} {desc.get('name')!r:32} {eid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
