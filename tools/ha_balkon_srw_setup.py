#!/usr/bin/env python3
"""Деплой и discover SRW-TH01 на балконе (локальный LAN)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]


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
        sys.exit("HA_TOKEN не задан")
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
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def entity_state(entity_id: str) -> str:
    try:
        return ha_request("GET", f"/api/states/{entity_id}")["state"]  # type: ignore[index]
    except Exception:
        return "missing"


def reload_core() -> None:
    try:
        ha_request("POST", "/api/services/homeassistant/reload_core_config", {})
        print("  homeassistant/reload_core_config: ok")
    except urllib.error.HTTPError as exc:
        print(f"  reload_core_config: {exc.code}")


def run_discover() -> int:
    print("==> discover (command_line sensor)")
    for svc, body in (
        ("shell_command/balkon_srw_discover", {}),
    ):
        try:
            ha_request("POST", f"/api/services/{svc}", body)
            print(f"  {svc}: ok")
            break
        except urllib.error.HTTPError as exc:
            print(f"  {svc}: {exc.code}")

    try:
        ha_request("POST", "/api/services/homeassistant/update_entity", {
            "entity_id": "sensor.balkon_srw_discover",
        })
        print("  update_entity sensor.balkon_srw_discover")
    except urllib.error.HTTPError as exc:
        print(f"  discover sensor missing: {exc.code}")
        return 1

    time.sleep(12)
    for entity in (
        "sensor.balkon_temperatura",
        "sensor.balkon_vlazhnost",
        "sensor.balkon_batareia",
    ):
        ha_request("POST", "/api/services/homeassistant/update_entity", {"entity_id": entity})
        time.sleep(2)

    temp = entity_state("sensor.balkon_temperatura")
    hum = entity_state("sensor.balkon_vlazhnost")
    print(f"  sensor.balkon_temperatura: {temp}")
    print(f"  sensor.balkon_vlazhnost: {hum}")
    return 0 if temp not in ("unknown", "unavailable", "none", "missing", "") else 1


def main() -> int:
    load_env()
    if os.environ.get("HA_SKIP_RELOAD") == "1":
        pass
    else:
        reload_core()
        time.sleep(3)
    rc = run_discover()
    if rc != 0:
        print("Discover не дал local_key. Пробуем продление cloud через tinytuya внутри HA…")
        # last resort message
        print("Если temp всё ещё unknown: iot.tuya.com → IoT Core → Extend Trial (бесплатно).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
