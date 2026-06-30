#!/usr/bin/env python3
"""Разовый fetch local_key + IP для SRW-TH01 через Tuya Cloud → .srw_local.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tinytuya_pkg"))
import tinytuya  # noqa: E402

DEVICE_ID = "bf86f3c7f53b7bb055f6x2"
CREDS = Path(__file__).with_name(".tuya_cloud.json")
OUT = Path(__file__).with_name(".srw_local.json")
ERR = Path(__file__).with_name("tuya_fetch_error.json")


def _fail(msg: dict) -> int:
    ERR.write_text(json.dumps(msg, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(msg))
    return 1


def _pick_key(row: dict) -> str | None:
    return row.get("local_key") or row.get("localKey") or row.get("local_key_new") or row.get("key")


def _scan_ip() -> tuple[str | None, str | None]:
    scanned = tinytuya.deviceScan(verbose=False)
    candidates: list[dict] = []
    if isinstance(scanned, dict):
        for gw, info in scanned.items():
            row = info if isinstance(info, dict) else {}
            candidates.append({"gwId": gw, **row})
    elif isinstance(scanned, list):
        candidates = [d for d in scanned if isinstance(d, dict)]
    for dev in candidates:
        gw = str(dev.get("gwId") or dev.get("id") or "")
        if gw.startswith(DEVICE_ID[:8]) or gw == DEVICE_ID:
            return dev.get("ip"), dev.get("version")
    return None, None


def _cloud_row(cloud: tinytuya.Cloud) -> dict | None:
    devs = cloud.getdevices()
    items = devs if isinstance(devs, list) else devs.get("result", [])
    if isinstance(items, dict):
        items = items.get("devices", items.get("list", []))
    for item in items:
        if not isinstance(item, dict):
            continue
        did = item.get("id") or item.get("device_id")
        if did == DEVICE_ID:
            return item
    for path in (f"/v1.0/devices/{DEVICE_ID}", f"/v1.0/iot-03/devices/{DEVICE_ID}"):
        try:
            data = cloud.cloudrequest(path)
            result = data.get("result", data) if isinstance(data, dict) else data
            if isinstance(result, dict):
                return result
        except Exception:
            continue
    return None


def main() -> int:
    try:
        creds = json.loads(CREDS.read_text())
        cloud = tinytuya.Cloud(
            apiRegion=creds.get("apiRegion", "eu"),
            apiKey=creds["apiKey"],
            apiSecret=creds["apiSecret"],
        )
        st = cloud.getstatus(DEVICE_ID)
        if not st or not st.get("success"):
            return _fail({"ok": False, "error": st})

        row = _cloud_row(cloud)
        if not row:
            return _fail({"ok": False, "error": "device not in cloud", "status": st})

        key = _pick_key(row)
        ip = row.get("ip") or row.get("ip_address") or "0.0.0.0"
        ver = row.get("version") or row.get("product_version") or "3.3"
        scan_ip, scan_ver = _scan_ip()
        if scan_ip:
            ip = scan_ip
            ver = scan_ver or ver
        if not key:
            return _fail({"ok": False, "error": "no local_key", "row_keys": sorted(row.keys()), "ip": ip})

        OUT.write_text(
            json.dumps({"ip": ip, "local_key": key, "version": str(ver)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        vals = {x["code"]: x["value"] for x in st.get("result", [])}
        ERR.unlink(missing_ok=True)
        print(json.dumps({"ok": True, "ip": ip, "version": ver, "temp": vals.get("va_temperature")}))
        return 0
    except Exception as exc:
        return _fail({"ok": False, "error": str(exc)[:300]})


if __name__ == "__main__":
    raise SystemExit(main())
