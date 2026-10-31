#!/usr/bin/env python3
"""Быстрое восстановление HA: туалет HOBEIAN + балкон SRW-TH01.

  cd /root/projects/empire && source .env
  python3 tools/ha_fix_now.py
  python3 tools/ha_fix_now.py --tualet-only
  python3 tools/ha_fix_now.py --balkon-scan
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

EMPIRE_DIR = Path(__file__).resolve().parents[1]
HOBEIAN_IEEE = "a4:c1:38:0f:14:db:5d:39"
DETSKAIA_IEEE = "a4:c1:38:14:a6:45:ff:ff"  # Детская T/H
SEMYON_IEEE = "a4:c1:38:14:9a:b5:ff:ff"  # Семён T/H
SRW_DEVICE_ID = "bf86f3c7f53b7bb055f6x2"
PERMIT_SEC = 254


def load_env() -> None:
    env_path = EMPIRE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ha_token() -> str:
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        sys.exit("HA_TOKEN не задан (.env)")
    return token


def ha_base() -> str:
    return os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")


def ha_request(method: str, path: str, body: dict | None = None) -> dict | list | None:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{ha_base()}{path}",
        data=data,
        headers={"Authorization": f"Bearer {ha_token()}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def entity_state(entity_id: str) -> str:
    try:
        return ha_request("GET", f"/api/states/{entity_id}")["state"]  # type: ignore[index]
    except urllib.error.HTTPError:
        return "missing"


async def zha_permit(seconds: int = PERMIT_SEC) -> bool:
    seconds = min(seconds, 254)
    try:
        ha_request("POST", "/api/services/zha/permit", {"duration": seconds})
        return True
    except urllib.error.HTTPError:
        pass
    if websockets is None:
        print("websockets не установлен: pip install websockets")
        return False
    ws_url = ha_base().replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": ha_token()}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            print("WebSocket auth failed")
            return False
        await ws.send(json.dumps({
            "id": 1,
            "type": "call_service",
            "domain": "zha",
            "service": "permit",
            "service_data": {"duration": seconds},
        }))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                return msg.get("success", False)
    return False


async def zha_reconfigure(ieee: str) -> bool:
    if websockets is None:
        print("websockets не установлен: pip install websockets")
        return False
    ws_url = ha_base().replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": ha_token()}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            print("WebSocket auth failed")
            return False
        await ws.send(json.dumps({"id": 1, "type": "zha/devices/reconfigure", "ieee": ieee}))
        ok = False
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                ok = msg.get("success", True)
                if msg.get("error"):
                    print("ZHA reconfigure error:", msg["error"])
                break
            if msg.get("type") == "event":
                print("ZHA event:", msg.get("event", {}).get("type"))
    time.sleep(12)
    return ok


def repair_tualet_pair() -> int:
    print("==> Туалет: удаление offline ZG-301Z + permit")
    try:
        ha_request("POST", "/api/services/zha/remove", {"ieee": HOBEIAN_IEEE})
        print("  zha.remove отправлен")
    except urllib.error.HTTPError as exc:
        print(f"  zha.remove: {exc.code} (возможно уже удалён)")
    time.sleep(4)
    ok = asyncio.run(zha_permit(PERMIT_SEC))
    print(f"  permit {PERMIT_SEC} с ({'OK' if ok else 'FAIL'}) — нажмите кнопку на выключателе туалета 5–10 с")
    print("  HA → Настройки → ZHA → Добавить устройство — если не появится само")
    return 0


def fix_tualet(repair: bool = False) -> int:
    if repair:
        return repair_tualet_pair()
    print("==> Туалет: HOBEIAN ZG-301Z (ZHA)")
    before = entity_state("light.hobeian_zg_301z")
    print(f"  light.hobeian_zg_301z: {before}")
    print(f"  light.empire_tualet_svet: {entity_state('light.empire_tualet_svet')}")

    if before not in ("unavailable", "unknown", "missing"):
        print("  Уже online — пропуск reconfigure")
        return 0

    print("  ZHA reconfigure…")
    asyncio.run(zha_reconfigure(HOBEIAN_IEEE))
    after = entity_state("light.hobeian_zg_301z")
    print(f"  после reconfigure: {after}")

    if after not in ("unavailable", "unknown", "missing"):
        ha_request("POST", "/api/services/homeassistant/update_entity", {
            "entity_id": ["light.hobeian_zg_301z", "light.empire_tualet_svet"],
        })
        print("  OK")
        return 0

    print("  Всё ещё offline. Запуск permit…")
    asyncio.run(zha_permit(120))
    print("  Нажмите кнопку на выключателе туалета 5–10 с (или HA → ZHA → Добавить устройство).")
    return 1


def scan_srw_on_ha() -> None:
    print("==> Балкон: скан SRW-TH01 в LAN (через SSH на HA)")
    import subprocess

    ssh = [
        "ssh",
        "-o", "ConnectTimeout=12",
        "-o", "BatchMode=yes",
        "-i", f"{Path.home()}/.ssh/id_ed25519",
        "-p", os.environ.get("HA_SSH_PORT", "22222"),
        f"root@{os.environ.get('HA_HOST', '100.80.133.85')}",
        "docker exec homeassistant python3 -c "
        + json.dumps(
            "import sys; sys.path.insert(0,'/config/scripts/tinytuya_pkg'); "
            "import tinytuya; "
            f"target='{SRW_DEVICE_ID}'; "
            "hits=[{k:d.get(k) for k in ('ip','gwId','version')} "
            "for d in tinytuya.deviceScan(verbose=False) if d.get('gwId','').startswith(target[:8])]; "
            "print('SCAN', hits or 'not_found')"
        ),
    ]
    try:
        out = subprocess.check_output(ssh, text=True, timeout=90, stderr=subprocess.STDOUT)
        print(out.strip())
    except subprocess.CalledProcessError as exc:
        print(exc.output or exc)
        print("Скан не удался — запустите на armbian: python3 -m tinytuya scan")


def fix_semyon(repair: bool = False) -> int:
    """Детская + Семён: оба CK-TLSR8656 по ZHA."""
    print("==> Детская / Семён: CK-TLSR8656 (ZHA)")
    pairs = (
        ("Детская", DETSKAIA_IEEE, "sensor.ewelink_ck_tlsr8656_ss5_01_7014_temperatura",
         "sensor.ewelink_ck_tlsr8656_ss5_01_7014_vlazhnost",
         "sensor.ewelink_ck_tlsr8656_ss5_01_7014_batareia"),
        ("Семён", SEMYON_IEEE, "sensor.ewelink_ck_tlsr8656_ss5_01_7014_temperatura_2",
         "sensor.ewelink_ck_tlsr8656_ss5_01_7014_vlazhnost_2",
         "sensor.ewelink_ck_tlsr8656_ss5_01_7014_batareia_2"),
    )
    rc = 0
    offline = []
    for label, ieee, temp_eid, hum_eid, bat_eid in pairs:
        temp = entity_state(temp_eid)
        print(f"  {label}: {temp_eid}={temp}")
        if temp not in ("unavailable", "unknown", "missing"):
            continue
        offline.append((label, ieee, temp_eid, hum_eid, bat_eid))

    if not offline:
        print("  Оба online — пропуск")
        return 0

    if repair:
        print("  remove + permit (на каждом датчике кнопка 5–10 с)")
        for label, ieee, *_ in offline:
            try:
                ha_request("POST", "/api/services/zha/remove", {"ieee": ieee})
                print(f"  zha.remove {label}")
            except urllib.error.HTTPError as exc:
                print(f"  zha.remove {label}: {exc.code}")
        time.sleep(4)
        ok = asyncio.run(zha_permit(PERMIT_SEC))
        print(f"  permit {PERMIT_SEC} с ({'OK' if ok else 'FAIL'})")
        return 0

    for label, ieee, temp_eid, hum_eid, bat_eid in offline:
        print(f"  ZHA reconfigure {label}…")
        asyncio.run(zha_reconfigure(ieee))
        for entity in (temp_eid, hum_eid, bat_eid):
            try:
                ha_request("POST", "/api/services/homeassistant/update_entity", {"entity_id": entity})
            except urllib.error.HTTPError:
                pass
        time.sleep(2)
        temp2 = entity_state(temp_eid)
        print(f"  после reconfigure {label}: {temp2}")
        if temp2 in ("unavailable", "unknown", "missing"):
            rc = 1

    if rc:
        print("  Всё ещё offline (сеть ZHA жива — кухня/спальня online).")
        print("  1) python3 tools/ha_fix_now.py --semyon-repair")
        print("  2) Зажмите кнопку на каждом датчике 5–10 с (permit ~4 мин)")
        print("  3) Проверьте батарейку (Семён offline с 23.09)")
    return rc


def fix_balkon() -> int:
    print("==> Балкон: SRW-TH01")
    temp = entity_state("sensor.balkon_temperatura")
    print(f"  sensor.balkon_temperatura: {temp}")

    for entity in (
        "sensor.balkon_temperatura",
        "sensor.balkon_vlazhnost",
        "sensor.balkon_batareia",
    ):
        try:
            ha_request("POST", "/api/services/homeassistant/update_entity", {"entity_id": entity})
            print(f"  update_entity {entity}")
        except urllib.error.HTTPError as exc:
            print(f"  update_entity {entity}: {exc.code}")

    time.sleep(3)
    temp2 = entity_state("sensor.balkon_temperatura")
    hum = entity_state("sensor.balkon_vlazhnost")
    print(f"  после опроса: temp={temp2}, hum={hum}")
    if temp2 not in ("unknown", "unavailable", "none", "missing", ""):
        return 0

    print("  Tuya Cloud подписка истекла (28841002).")
    print("  Варианты:")
    print("    1) iot.tuya.com → Cloud → продлить IoT Core (быстро)")
    print("    2) LocalTuya: python3 tools/ha_fix_now.py --balkon-scan → /config/scripts/.srw_local.json")
    return 1


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--tualet-only", action="store_true")
    parser.add_argument("--balkon-only", action="store_true")
    parser.add_argument("--balkon-scan", action="store_true")
    parser.add_argument("--tualet-repair", action="store_true", help="remove + permit ZG-301Z")
    parser.add_argument("--semyon-only", action="store_true")
    parser.add_argument("--semyon-repair", action="store_true", help="remove + permit CK-TLSR8656")
    args = parser.parse_args()

    rc = 0
    if args.balkon_scan:
        scan_srw_on_ha()
        return 0
    if not args.balkon_only and not args.semyon_only:
        rc = max(rc, fix_tualet(repair=args.tualet_repair))
    if not args.tualet_only and not args.semyon_only:
        rc = max(rc, fix_balkon())
    if not args.tualet_only and not args.balkon_only:
        rc = max(rc, fix_semyon(repair=args.semyon_repair))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
