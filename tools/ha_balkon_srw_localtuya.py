#!/usr/bin/env python3
"""SRW-TH01 → LocalTuya + template sensor.balkon_temperatura (без облака).

  cd /root/projects/empire && source .env
  bash deploy/ha_deploy_balkon_localtuya.sh
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]
LOCALTUYA_ENTRY = "01F1XRJS41AC54X2WPAEHVBMS1"
SRW_ID = "bf86f3c7f53b7bb055f6x2"


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


def ha_request(method: str, path: str, body: dict | None = None):
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


def sensor_entity(dp: int, friendly_name: str, device_class: str, unit: str, scaling: float | None = None) -> dict:
    ent = {
        "id": str(dp),
        "platform": "sensor",
        "friendly_name": friendly_name,
        "device_class": device_class,
        "state_class": "measurement",
        "unit_of_measurement": unit,
        "is_passive_entity": True,
        "restore_on_reconnect": False,
    }
    if scaling is not None:
        ent["scaling"] = scaling
    if device_class == "battery":
        ent["entity_category"] = "diagnostic"
    return ent


def srw_device_cfg(ip: str, key: str, version: str, dps_strings: list[str]) -> dict:
    return {
        "friendly_name": "SRW-TH01 Балкон",
        "host": ip if ip and ip not in ("0.0.0.0", "") else "auto",
        "device_id": SRW_ID,
        "local_key": key,
        "protocol_version": version or "3.3",
        "enable_debug": False,
        "scan_interval": 120,
        "device_sleep_time": 300,
        "model": "SRW-TH01",
        "product_name": "T & H Sensor",
        "dps_strings": dps_strings,
        "entities": [
            sensor_entity(1, "Балкон t° raw", "temperature", "°C", 0.1),
            sensor_entity(2, "Балкон влажн raw", "humidity", "%"),
            sensor_entity(4, "Балкон батарея raw", "battery", "%"),
        ],
    }


def load_srw_creds(config_path: Path) -> tuple[str, str, str]:
    ip = os.environ.get("SRW_IP", "")
    key = os.environ.get("SRW_KEY", "")
    ver = os.environ.get("SRW_VERSION", "3.3")
    local_json = EMPIRE_DIR / ".srw_local.json"
    if local_json.exists():
        data = json.loads(local_json.read_text())
        ip = ip or data.get("ip", "")
        key = key or data.get("local_key", "")
        ver = data.get("version") or ver
    if key and ip and ip not in ("0.0.0.0", ""):
        return ip, key, ver

    # fetch via HA shell (runs inside homeassistant container)
    print("==> fetch local_key через Tuya Cloud на HA…")
    try:
        ha_request("POST", "/api/services/shell_command/balkon_srw_fetch_key", {})
    except urllib.error.HTTPError as exc:
        print(f"  fetch_key service: {exc.code}")
    time.sleep(5)

    import subprocess

    ssh = [
        "ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes",
        "-i", f"{Path.home()}/.ssh/id_ed25519",
        "-p", os.environ.get("HA_SSH_PORT", "22222"),
        f"root@{os.environ.get('HA_HOST', '100.80.133.85')}",
        "cat /config/scripts/.srw_local.json 2>/dev/null",
    ]
    try:
        out = subprocess.check_output(ssh, text=True, timeout=20)
        data = json.loads(out)
        return data.get("ip", ip), data.get("local_key", key), data.get("version", ver)
    except Exception as exc:
        print(f"  .srw_local.json на HA: {exc}")
        sys.exit("Нет local_key. Продление IoT Core ещё не активно — подождите 1–2 ч или нажмите кнопку на датчике и повторите.")


def patch_localtuya(config_path: Path, ip: str, key: str, version: str) -> None:
    store = json.loads(config_path.read_text())
    lt = next(e for e in store["data"]["entries"] if e.get("domain") == "localtuya")
    devices = lt["data"]["devices"]
    dps = [
        "1 (value: 0)",
        "2 (value: 0)",
        "4 (value: 0)",
    ]
    devices[SRW_ID] = srw_device_cfg(ip, key, version, dps)
    lt["data"]["updated_at"] = str(int(time.time() * 1000))
    lt["modified_at"] = datetime.now(timezone.utc).isoformat()
    config_path.write_text(json.dumps(store, indent=2))
    print(f"==> LocalTuya: SRW-TH01 @ {ip or '0.0.0.0'} v{version}")


def patch_entity_names(entity_path: Path) -> None:
    store = json.loads(entity_path.read_text())
    mapping = {
        f"local_{SRW_ID}_1": ("sensor.balkon_srw_temp_raw", "balkon", "t°"),
        f"local_{SRW_ID}_2": ("sensor.balkon_srw_hum_raw", "balkon", "влажн"),
        f"local_{SRW_ID}_4": ("sensor.balkon_srw_bat_raw", "balkon", "батарея"),
    }
    for ent in store["data"]["entities"]:
        uid = ent.get("unique_id", "")
        if uid not in mapping:
            continue
        eid, area, name = mapping[uid]
        ent["entity_id"] = eid
        ent["area_id"] = area
        ent["name"] = name
        print(f"  entity {uid} → {eid}")
    entity_path.write_text(json.dumps(store, indent=2))


def main() -> int:
    load_env()
    config_path = Path(os.environ.get("HA_CONFIG_ENTRIES", "/tmp/ha_config_entries.json"))
    entity_path = Path(os.environ.get("HA_ENTITY_REGISTRY", "/tmp/ha_entity_registry.json"))
    if not config_path.exists():
        sys.exit(f"Нет {config_path} — сначала scp с HA")

    ip, key, ver = load_srw_creds(config_path)
    if not key:
        sys.exit("local_key пустой")
    patch_localtuya(config_path, ip, key, ver)

    if entity_path.exists():
        print("==> Entity registry (после reload появятся сущности)")
        # rename only if entities already exist
        try:
            patch_entity_names(entity_path)
        except Exception as exc:
            print(f"  skip rename: {exc}")

    print("==> Reload LocalTuya")
    ha_request("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": LOCALTUYA_ENTRY})
    time.sleep(12)
    ha_request("POST", "/api/services/template/reload", {})
    time.sleep(3)

    for eid in ("sensor.balkon_temperatura", "sensor.balkon_vlazhnost", "sensor.balkon_srw_temp_raw"):
        try:
            st = ha_request("GET", f"/api/states/{eid}")["state"]
            print(f"  {eid}: {st}")
        except Exception:
            print(f"  {eid}: missing (переименуйте entity после появления local_*)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
