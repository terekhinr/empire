#!/usr/bin/env python3
"""Починка Алиса → Yaha Cloud → свет кухня/туалет."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import websockets
except ImportError:
    sys.exit("pip install websockets")

ROOT = Path(__file__).resolve().parents[1]
YAML = ROOT / "homeassistant" / "yandex_smart_home.yaml"
ENTRY_ID = "01KRZWQPJBMBDSE4GGXWKW039M"
LIGHTS = ("light.empire_kuhnya_svet", "light.empire_tualet_svet")
AREA_NAMES = {"light.empire_kuhnya_svet": "Кухня", "light.empire_tualet_svet": "Туалет"}


def env(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    dot = ROOT / ".env"
    if dot.is_file():
        for line in dot.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def api(method: str, path: str, body: dict | None = None, timeout: int = 60):
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    if not base or not token:
        sys.exit("HA_URL и HA_TOKEN обязательны")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


async def ws_session():
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    ws = await websockets.connect(ws_url)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    if json.loads(await ws.recv()).get("type") != "auth_ok":
        await ws.close()
        raise RuntimeError("HA websocket auth failed")
    return ws


async def ws_call(ws, msg: dict) -> dict:
    req_id = msg["id"]
    await ws.send(json.dumps(msg))
    while True:
        r = json.loads(await ws.recv())
        if r.get("id") == req_id:
            return r


def scp_to_ha(local: Path, remote: str) -> None:
    host = env("HA_SSH") or "root@100.80.133.85"
    port = env("HA_SSH_PORT") or "22222"
    key = env("HA_SSH_KEY") or str(Path.home() / ".ssh/id_ed25519")
    subprocess.run(
        ["scp", "-P", port, "-i", key, str(local), f"{host}:{remote}"],
        check=True,
        capture_output=True,
    )


def patch_config_entries(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = next(e for e in data["data"]["entries"] if e.get("domain") == "yandex_smart_home")
    entry.setdefault("data", {})
    entry["data"]["linked_platforms"] = ["yandex"]
    opts = dict(entry.get("options") or {})
    opts["filter_source"] = "yaml"
    entry["options"] = opts
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cloud_token_works(token: str) -> bool:
    try:
        import aiohttp

        async def _probe() -> bool:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    "https://yaha-cloud.ru/api/home_assistant/v1/connect",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                ):
                    return True

        return asyncio.run(_probe())
    except Exception:
        return False


def reset_cloud_token(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = next(e for e in data["data"]["entries"] if e.get("domain") == "yandex_smart_home")
    ci = entry["data"]["cloud_instance"]
    if cloud_token_works(ci["token"]):
        return False
    req = urllib.request.Request(
        f"https://yaha-cloud.ru/api/home_assistant/v1/instance/{ci['id']}/reset-connection-token",
        data=b"",
        headers={"Authorization": f"Bearer {ci['token']}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        new = json.loads(resp.read())
    ci["token"] = new["connection_token"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


async def assign_areas(ws) -> None:
    areas = (await ws_call(ws, {"id": 20, "type": "config/area_registry/list"})).get("result", [])
    by_name = {a.get("name"): a.get("area_id") for a in areas}
    for eid, room in AREA_NAMES.items():
        area_id = by_name.get(room)
        if not area_id:
            print(f"  WARN: область «{room}» не найдена в HA")
            continue
        r = await ws_call(
            ws,
            {
                "id": 30,
                "type": "config/entity_registry/update",
                "entity_id": eid,
                "area_id": area_id,
            },
        )
        if not r.get("success", True):
            print(f"  WARN: area update {eid}: {r}")
        else:
            print(f"  OK area {eid} → {room}")


def verify_yandex_devices() -> dict[str, str]:
    diag = api("GET", f"/api/diagnostics/config_entry/{ENTRY_ID}")
    devices = diag.get("data", {}).get("devices", {})
    out = {}
    for eid in LIGHTS:
        d = devices.get(eid, {}).get("description", {})
        out[eid] = f"{d.get('room')} / {d.get('name')}" if d else "MISSING"
    return out


def test_lights() -> None:
    for eid in LIGHTS:
        before = api("GET", f"/api/states/{eid}")["state"]
        api("POST", "/api/services/light/turn_on", {"entity_id": eid}, timeout=90)
        time.sleep(6)
        after = api("GET", f"/api/states/{eid}")["state"]
        api("POST", "/api/services/light/turn_off", {"entity_id": eid}, timeout=60)
        print(f"  {eid}: {before} → {after}")


async def main() -> int:
    print("1) deploy yandex_smart_home.yaml")
    scp_to_ha(YAML, "/homeassistant/yandex_smart_home.yaml")

    host = env("HA_SSH") or "root@100.80.133.85"
    port = env("HA_SSH_PORT") or "22222"
    key = env("HA_SSH_KEY") or str(Path.home() / ".ssh/id_ed25519")
    local_ce = Path("/tmp/ha_ce_alice_fix.json")
    subprocess.run(
        ["scp", "-P", port, "-i", key, f"{host}:/homeassistant/.storage/core.config_entries", str(local_ce)],
        check=True,
        capture_output=True,
    )

    print("2) linked_platforms + cloud token")
    patch_config_entries(local_ce)
    try:
        if reset_cloud_token(local_ce):
            print("   cloud token reset (was invalid)")
        else:
            print("   cloud token OK, no reset")
    except urllib.error.HTTPError as e:
        print(f"   cloud token reset failed: {e}")

    subprocess.run(
        ["scp", "-P", port, "-i", key, str(local_ce), f"{host}:/homeassistant/.storage/core.config_entries"],
        check=True,
        capture_output=True,
    )

    print("3) areas + reload Yandex")
    ws = await ws_session()
    try:
        await assign_areas(ws)
    finally:
        await ws.close()

    api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": ENTRY_ID})
    time.sleep(4)
    try:
        api("POST", "/api/services/yandex_smart_home/reload", {})
    except urllib.error.HTTPError:
        pass
    time.sleep(8)

    print("4) Yandex exposes:")
    for eid, desc in verify_yandex_devices().items():
        print(f"   {eid}: {desc}")

    print("5) HA light test:")
    test_lights()

    print("\nГотово. Свет в Алисе: «включи свет на кухне» / «включи свет в туалете».")
    print("Если в приложении «Дом с Алисой» ещё нет комнат — Yaha Cloud → Обновить список устройств (один раз).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
