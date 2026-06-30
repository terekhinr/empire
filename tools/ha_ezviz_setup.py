#!/usr/bin/env python3
"""Ezviz: интеграция через HA config flow + переименование entity для панели.

Переменные (или /config/secrets.yaml на HA):
  EZVIZ_USERNAME, EZVIZ_PASSWORD
  EZVIZ_URL=apirus.ezvizru.com   # РФ по умолчанию

Запуск:
  cd /root/projects/empire && source .env
  EZVIZ_USERNAME=... EZVIZ_PASSWORD=... python3 tools/ha_ezviz_setup.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

EMPIRE_DIR = Path(__file__).resolve().parents[1]

CAMERA_TARGETS = {
    "ulica": ["улиц", "ulica", "street", "calle", "двор", "yard"],
    "podezd": ["подъезд", "podezd", "парадн", "entrance", "hall", "двер"],
}

# serial → (local_ip sensor suffix, entity slot)
EZVIZ_CAMERAS = {
    "BF0241992": ("h1c_bf0241992", "ulica"),
    "BF5488322": ("h1c_bf5488322", "podezd"),
}


def camera_local_ips(base: str, token: str) -> dict[str, str]:
    states = api_get(base, token, "/api/states")
    ips: dict[str, str] = {}
    for serial, (prefix, _slot) in EZVIZ_CAMERAS.items():
        eid = f"sensor.{prefix}_local_ip"
        for st in states:
            if st.get("entity_id") == eid:
                ip = str(st.get("state", "")).strip()
                if ip and ip not in ("unknown", "unavailable"):
                    ips[serial] = ip
    return ips


async def fix_empty_camera_entries(base: str, token: str, codes: dict[str, str]) -> int:
    """Починить RTSP entries с пустым data (баг Ezviz / HA issue #140340)."""
    if websockets is None:
        return 0
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    fixed = 0
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")
        resp = await ws_call(ws, 1, {"type": "config_entries/get"})
        entries = [
            e
            for e in resp.get("result", [])
            if e.get("domain") == "ezviz"
            and (e.get("unique_id") in EZVIZ_CAMERAS or e.get("title") in EZVIZ_CAMERAS)
        ]
        mid = 1
        for entry in entries:
            serial = entry.get("unique_id") or entry.get("title")
            data = entry.get("data") or {}
            if data.get("username") == "admin" and data.get("password"):
                continue
            code = codes.get(serial)
            if not code:
                continue
            mid += 1
            await ws_call(
                ws,
                mid,
                {
                    "type": "config_entries/update",
                    "entry_id": entry["entry_id"],
                    "data": {
                        "username": "admin",
                        "password": code,
                        "type": "CAMERA_ACCOUNT",
                    },
                    "options": {
                        "ffmpeg_arguments": entry.get("options", {}).get("ffmpeg_arguments", ""),
                        "timeout": entry.get("options", {}).get("timeout", 25),
                    },
                },
            )
            print(f"  fix entry {serial}: credentials applied")
            fixed += 1
    return fixed


async def list_ezviz_flows(base: str, token: str) -> list[dict]:
    if websockets is None:
        return []
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")
        resp = await ws_call(ws, 1, {"type": "config_entries/flow/progress"})
        return [f for f in resp.get("result", []) if f.get("handler") == "ezviz" and f.get("step_id") == "confirm"]


def configure_camera_rtsp(
    base: str,
    token: str,
    flow_id: str,
    serial: str,
    verify_code: str,
) -> None:
    """Завершить pending integration_discovery flow: admin + verification code."""
    step = api_post(
        base,
        token,
        f"/api/config/config_entries/flow/{flow_id}",
        {"username": "admin", "password": verify_code},
    )
    if step.get("type") == "create_entry":
        print(f"  RTSP {serial}: ok")
        return
    errors = step.get("errors") or step
    raise RuntimeError(f"RTSP {serial}: {errors}")


async def configure_cameras_async(base: str, token: str, codes: dict[str, str]) -> None:
    entries = api_get(base, token, "/api/config/config_entries/entry")
    configured = {
        e.get("title")
        for e in entries
        if e.get("domain") == "ezviz" and e.get("title") in EZVIZ_CAMERAS
    }
    flows = await list_ezviz_flows(base, token)
    if not flows and not configured:
        raise RuntimeError("Нет pending flow Ezviz — перезагрузите интеграцию в HA")

    for flow in flows:
        serial = flow.get("context", {}).get("unique_id", "")
        if serial in configured:
            print(f"  RTSP {serial}: уже настроена")
            continue
        code = codes.get(serial)
        if not code:
            raise RuntimeError(f"Нет verification code для {serial}")
        fid = flow["flow_id"]
        try:
            configure_camera_rtsp(base, token, fid, serial, code)
        except Exception as exc:
            alt = codes.get("BF5488322" if serial == "BF0241992" else "BF0241992")
            if alt and alt != code:
                print(f"  RTSP {serial}: retry с другим кодом")
                configure_camera_rtsp(base, token, fid, serial, alt)
            else:
                raise exc


def configure_cameras(base: str, token: str, codes: dict[str, str]) -> None:
    asyncio.run(configure_cameras_async(base, token, codes))


def ha_env() -> tuple[str, str]:
    url = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    env_file = EMPIRE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("HA_URL=") and not url:
                url = line.split("=", 1)[1].strip().rstrip("/")
            if line.startswith("HA_TOKEN=") and not token:
                token = line.split("=", 1)[1].strip()
    if not token:
        sys.exit("HA_TOKEN не задан")
    return url, token


def ezviz_creds() -> tuple[str, str, str]:
    user = os.environ.get("EZVIZ_USERNAME", "")
    pwd = os.environ.get("EZVIZ_PASSWORD", "")
    url = os.environ.get("EZVIZ_URL", "apirus.ezvizru.com")
    secrets = Path(os.environ.get("HA_SECRETS", "/config/secrets.yaml"))
    if secrets.is_file():
        for line in secrets.read_text().splitlines():
            line = line.strip()
            if line.startswith("ezviz_username:") and not user:
                user = line.split(":", 1)[1].strip().strip("'\"")
            if line.startswith("ezviz_password:") and not pwd:
                pwd = line.split(":", 1)[1].strip().strip("'\"")
            if line.startswith("ezviz_url:") and url == "apirus.ezvizru.com":
                url = line.split(":", 1)[1].strip().strip("'\"")
    if user.startswith("!secret "):
        user = ""
    if pwd.startswith("!secret "):
        pwd = ""
    return user, pwd, url


def api_post(base: str, token: str, path: str, data: dict | None = None) -> dict:
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def api_get(base: str, token: str, path: str) -> dict | list:
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def has_ezviz_entry(base: str, token: str) -> bool:
    try:
        entries = api_get(base, token, "/api/config/config_entries/entry")
        return any(e.get("domain") == "ezviz" for e in entries)
    except Exception:
        return False


def setup_ezviz(base: str, token: str, user: str, pwd: str, url: str) -> None:
    if has_ezviz_entry(base, token):
        print("  Ezviz уже подключён")
        return
    flow = api_post(base, token, "/api/config/config_entries/flow", {"handler": "ezviz"})
    flow_id = flow["flow_id"]
    step = api_post(
        base,
        token,
        f"/api/config/config_entries/flow/{flow_id}",
        {"username": user, "password": pwd, "url": url},
    )
    if step.get("type") == "create_entry":
        print("  Ezviz: интеграция создана")
        return
    if step.get("type") == "form":
        raise RuntimeError(f"Ezviz flow не завершён: {step.get('errors') or step}")
    if step.get("type") == "abort":
        raise RuntimeError(f"Ezviz abort: {step.get('reason')}")
    print(f"  Ezviz step: {step.get('type')}")


def guess_slot(name: str) -> str | None:
    low = name.lower()
    for slot, keys in CAMERA_TARGETS.items():
        if any(k in low for k in keys):
            return slot
    return None


async def ws_call(ws, msg_id: int, payload: dict) -> dict:
    payload = dict(payload)
    payload["id"] = msg_id
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
            if not data.get("success", True):
                raise RuntimeError(data.get("error", data))
            return data


async def rename_entities(base: str, token: str) -> int:
    if websockets is None:
        print("  pip install websockets — пропуск rename")
        return 0
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    renamed = 0
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")
        mid = 1
        resp = await ws_call(ws, mid, {"type": "config/entity_registry/list"})
        entities = resp.get("result", [])
        cameras = [e for e in entities if e.get("entity_id", "").startswith("camera.")]
        motions = [e for e in entities if e.get("entity_id", "").startswith("binary_sensor.") and "motion" in e.get("entity_id", "")]
        used: set[str] = set()

        for cam in cameras:
            name = cam.get("name") or cam.get("original_name") or cam.get("entity_id", "")
            slot = guess_slot(name)
            if not slot or slot in used:
                continue
            target = f"camera.ezviz_{slot}"
            if cam["entity_id"] == target:
                used.add(slot)
                continue
            mid += 1
            await ws_call(
                ws,
                mid,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": cam["entity_id"],
                    "new_entity_id": target,
                    "name": "Улица" if slot == "ulica" else "Подъезд",
                },
            )
            print(f"  rename {cam['entity_id']} → {target}")
            renamed += 1
            used.add(slot)

        # Если имена не угадали — первые две камеры по порядку
        remaining = [c for c in cameras if not c["entity_id"].startswith("camera.ezviz_")]
        for slot in ("ulica", "podezd"):
            if slot in used:
                continue
            if not remaining:
                break
            cam = remaining.pop(0)
            target = f"camera.ezviz_{slot}"
            mid += 1
            await ws_call(
                ws,
                mid,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": cam["entity_id"],
                    "new_entity_id": target,
                    "name": "Улица" if slot == "ulica" else "Подъезд",
                },
            )
            print(f"  rename (fallback) {cam['entity_id']} → {target}")
            renamed += 1

        for mot in motions:
            low = (mot.get("name") or mot.get("entity_id", "")).lower()
            slot = guess_slot(low)
            if not slot:
                # привязка по device_id к камере
                dev = mot.get("device_id")
                for cam in cameras:
                    if cam.get("device_id") == dev:
                        eid = cam.get("entity_id", "")
                        if "ulica" in eid:
                            slot = "ulica"
                        elif "podezd" in eid:
                            slot = "podezd"
                if not slot and len(cameras) == 2:
                    idx = motions.index(mot) if mot in motions else 0
                    slot = "ulica" if idx == 0 else "podezd"
            if not slot:
                continue
            target = f"binary_sensor.ezviz_{slot}_motion_alarm"
            if mot["entity_id"] == target:
                continue
            if "motion" not in mot.get("entity_id", "") and "alarm" not in mot.get("entity_id", ""):
                continue
            try:
                mid += 1
                await ws_call(
                    ws,
                    mid,
                    {
                        "type": "config/entity_registry/update",
                        "entity_id": mot["entity_id"],
                        "new_entity_id": target,
                    },
                )
                print(f"  rename {mot['entity_id']} → {target}")
                renamed += 1
            except Exception as exc:
                print(f"  skip motion {mot['entity_id']}: {exc}")
    return renamed


def main() -> int:
    base, token = ha_env()
    user, pwd, url = ezviz_creds()

    # Коды верификации с наклеек: EZVIZ_CAM_BF0241992 / EZVIZ_CAM_BF5488322
    codes = {
        "BF0241992": os.environ.get("EZVIZ_CAM_BF0241992", "BNATXF"),
        "BF5488322": os.environ.get("EZVIZ_CAM_BF5488322", "PPNTGB"),
    }
    secrets = Path(os.environ.get("HA_SECRETS", "/config/secrets.yaml"))
    if secrets.is_file():
        for line in secrets.read_text().splitlines():
            line = line.strip()
            if line.startswith("ezviz_cam_bf0241992:"):
                codes["BF0241992"] = line.split(":", 1)[1].strip().strip("'\"")
            if line.startswith("ezviz_cam_bf5488322:"):
                codes["BF5488322"] = line.split(":", 1)[1].strip().strip("'\"")

    print("==> Ezviz setup")
    if user and pwd:
        try:
            setup_ezviz(base, token, user, pwd, url)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()[:300]
            print(f"  Ezviz API error {exc.code}: {body}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"  Ezviz: {exc}", file=sys.stderr)
            return 1
    else:
        if has_ezviz_entry(base, token):
            print("  Ezviz уже есть, creds не нужны")
        else:
            print("  Нет EZVIZ_USERNAME/PASSWORD — добавьте в /config/secrets.yaml:")
            print("    ezviz_username: '...'")
            print("    ezviz_password: '...'")
            print("    ezviz_url: apirus.ezvizru.com")
            return 2

    print("==> RTSP камеры (verification code)")
    try:
        configure_cameras(base, token, codes)
    except Exception as exc:
        print(f"  RTSP: {exc}", file=sys.stderr)
        print("  Проверьте: Ezviz app → LAN Live View → Local Service Settings → RTSP ON")
        print("  Порт 554 на камерах должен быть открыт")

    if websockets is not None:
        try:
            fixed = asyncio.run(fix_empty_camera_entries(base, token, codes))
            if fixed:
                entries = api_get(base, token, "/api/config/config_entries/entry")
                main = next(
                    (e["entry_id"] for e in entries if e.get("domain") == "ezviz" and e.get("source") == "user"),
                    None,
                )
                if main:
                    api_post(base, token, "/api/services/homeassistant/reload_config_entry", {"entry_id": main})
                    print(f"  reload main ezviz entry после fix ({fixed})")
        except Exception as exc:
            print(f"  fix entries: {exc}", file=sys.stderr)

    print("==> Переименование entity")
    import time
    time.sleep(3)
    renamed = asyncio.run(rename_entities(base, token))
    print(f"  переименовано: {renamed}")

    for svc in ("automation/reload",):
        try:
            api_post(base, token, f"/api/services/{svc}")
            print(f"  {svc}: ok")
        except Exception as exc:
            print(f"  {svc}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
