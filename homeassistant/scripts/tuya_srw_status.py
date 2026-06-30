#!/usr/bin/env python3
"""Poll SRW-TH01: local LAN first, then Tuya Cloud fallback."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tinytuya_pkg"))
import tinytuya  # noqa: E402

DEVICE_ID = "bf86f3c7f53b7bb055f6x2"
CREDS = Path(__file__).with_name(".tuya_cloud.json")
LOCAL = Path(__file__).with_name(".srw_local.json")
LOG = Path(__file__).with_name("tuya_last_error.txt")
LOCALTUYA_STORE = Path("/config/.storage/core.config_entries")

TEMP_KEYS = ("va_temperature", "temp_current", "temperature", "1")
HUM_KEYS = ("va_humidity", "humidity_value", "humidity", "2")
BAT_KEYS = ("battery_percentage", "battery", "battery_state", "4")
PROTOCOLS = ("3.3", "3.4", "3.5", "3.2", "3.1")


def _pick(values: dict, keys: tuple[str, ...], default=0):
    for key in keys:
        if key in values and values[key] is not None:
            return values[key]
    return default


def _parse_temp(raw) -> float:
    val = float(raw)
    return round(val / 10.0, 1) if val > 100 else round(val, 1)


def _fail(msg: str) -> int:
    LOG.write_text(msg[:500], encoding="utf-8")
    print("unavailable")
    print(msg, file=sys.stderr)
    return 1


def _cloud(creds: dict) -> tinytuya.Cloud:
    return tinytuya.Cloud(
        apiRegion=creds.get("apiRegion", "eu"),
        apiKey=creds["apiKey"],
        apiSecret=creds["apiSecret"],
    )


def _read_values_cloud(cloud: tinytuya.Cloud) -> dict:
    data = cloud.getstatus(DEVICE_ID)
    if not data or not data.get("success"):
        raise RuntimeError(f"getstatus failed: {data}")
    return {item["code"]: item["value"] for item in data.get("result", [])}


def _read_values_local(cfg: dict) -> dict:
    ver = cfg.get("version") or "3.3"
    dev = tinytuya.Device(DEVICE_ID, cfg["ip"], cfg["local_key"], version=ver)
    dev.set_socketTimeout(8)
    dev.set_socketRetryLimit(2)
    st = dev.status()
    if not st or "Error" in str(st):
        raise RuntimeError(f"local status failed: {st}")
    dps = st.get("dps", st)
    if "dps" in dps:
        dps = dps["dps"]
    mapping = {
        "1": "va_temperature",
        "2": "va_humidity",
        "4": "battery_percentage",
    }
    return {mapping.get(str(k), str(k)): v for k, v in dps.items()}


def _scan_ip() -> tuple[str | None, str | None]:
    scanned = tinytuya.deviceScan(verbose=False)
    candidates: list[dict] = []
    if isinstance(scanned, dict):
        for gw, info in scanned.items():
            row = info if isinstance(info, dict) else {}
            row = {"gwId": gw, **row}
            candidates.append(row)
    elif isinstance(scanned, list):
        candidates = [d for d in scanned if isinstance(d, dict)]
    for dev in candidates:
        gw = str(dev.get("gwId") or dev.get("id") or "")
        if gw.startswith(DEVICE_ID[:8]) or gw == DEVICE_ID:
            return dev.get("ip"), dev.get("version")
    return None, None


def _localtuya_keys() -> list[tuple[str, str]]:
    if not LOCALTUYA_STORE.exists():
        return []
    try:
        store = json.loads(LOCALTUYA_STORE.read_text())
        lt = next(e for e in store["data"]["entries"] if e.get("domain") == "localtuya")
        return [(d.get("local_key", ""), d.get("protocol_version") or "3.3")
                for d in lt["data"].get("devices", {}).values() if d.get("local_key")]
    except Exception:
        return []


def _cloud_device_key(cloud: tinytuya.Cloud) -> tuple[str | None, str | None]:
    for fn in (
        lambda: cloud.getdevices(),
        lambda: cloud.cloudrequest(f"/v1.0/users/{cloud.uid}/devices"),
    ):
        try:
            data = fn()
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("result", data)
                if isinstance(items, dict):
                    items = items.get("devices", items.get("list", []))
            else:
                continue
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                did = item.get("id") or item.get("device_id")
                if did != DEVICE_ID:
                    continue
                return item.get("local_key") or item.get("localKey") or item.get("key"), item.get("version") or item.get("product_version")
        except Exception:
            continue
    return None, None


def _probe_local(ip: str, local_key: str, version: str | None = None) -> dict | None:
    versions = [version] if version else list(PROTOCOLS)
    for ver in versions:
        if not ver:
            continue
        try:
            return _read_values_local({"ip": ip, "local_key": local_key, "version": ver})
        except Exception:
            continue
    return None


def _discover_local_cfg() -> dict | None:
    ip, ver = _scan_ip()
    if not ip:
        return None

    if LOCAL.exists():
        cfg = json.loads(LOCAL.read_text())
        if cfg.get("ip") == ip and cfg.get("local_key"):
            values = _probe_local(ip, cfg["local_key"], cfg.get("version") or ver)
            if values:
                cfg["version"] = cfg.get("version") or ver or "3.3"
                return cfg

    if CREDS.exists():
        try:
            cloud = _cloud(json.loads(CREDS.read_text()))
            key, cloud_ver = _cloud_device_key(cloud)
            if key:
                values = _probe_local(ip, key, cloud_ver or ver)
                if values:
                    return {"ip": ip, "local_key": key, "version": cloud_ver or ver or "3.3"}
        except Exception:
            pass

    for key, key_ver in _localtuya_keys():
        values = _probe_local(ip, key, key_ver or ver)
        if values:
            return {"ip": ip, "local_key": key, "version": key_ver or ver or "3.3"}

    return {"ip": ip, "version": ver or "3.3", "local_key": None}


def discover_and_save() -> int:
    found = _discover_local_cfg()
    if not found:
        return _fail("SRW-TH01 not found in LAN scan")
    if not found.get("local_key"):
        return _fail(f"SRW @ {found.get('ip')} found, local_key missing (renew iot.tuya.com or tinytuya wizard)")
    values = _probe_local(found["ip"], found["local_key"], found.get("version"))
    if not values:
        return _fail("SRW found but local status probe failed")
    LOCAL.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.unlink(missing_ok=True)
    print(json.dumps({
        "ip": found["ip"],
        "version": found.get("version"),
        "temp": _parse_temp(_pick(values, TEMP_KEYS)),
        "humidity": int(_pick(values, HUM_KEYS)),
    }))
    return 0


def _local_cfg_valid(cfg: dict) -> bool:
    ip = (cfg.get("ip") or "").strip()
    return bool(ip and ip not in ("0.0.0.0", "127.0.0.1") and cfg.get("local_key"))


def _read_values() -> tuple[dict, str]:
    if LOCAL.exists():
        cfg = json.loads(LOCAL.read_text())
        if _local_cfg_valid(cfg):
            try:
                return _read_values_local(cfg), "local"
            except Exception as local_exc:
                if not CREDS.exists():
                    raise local_exc
    if not CREDS.exists():
        raise RuntimeError("no cloud creds and no valid local cfg")
    creds = json.loads(CREDS.read_text())
    return _read_values_cloud(_cloud(creds)), "cloud"


def main() -> int:
    metric = sys.argv[1] if len(sys.argv) > 1 else "json"
    try:
        if metric == "discover":
            return discover_and_save()
        if metric == "diag":
            out = {"device": DEVICE_ID, "local_cfg": LOCAL.exists(), "cloud_cfg": CREDS.exists()}
            if CREDS.exists():
                creds = json.loads(CREDS.read_text())
                cloud = _cloud(creds)
                out["region"] = creds.get("apiRegion", "eu")
                out["connect"] = cloud.getconnectstatus(DEVICE_ID)
                try:
                    out["status"] = cloud.getstatus(DEVICE_ID)
                except Exception as exc:
                    out["status_error"] = str(exc)[:300]
            if LOCAL.exists():
                out["local"] = json.loads(LOCAL.read_text())
                try:
                    values = _read_values_local(out["local"])
                    out["local_ok"] = {
                        "temp": _parse_temp(_pick(values, TEMP_KEYS)),
                        "humidity": int(_pick(values, HUM_KEYS)),
                        "battery": int(_pick(values, BAT_KEYS)),
                        "codes": list(values.keys()),
                    }
                except Exception as exc:
                    out["local_error"] = str(exc)[:300]
            try:
                values, source = _read_values()
                out["source"] = source
                out["parsed"] = {
                    "temp": _parse_temp(_pick(values, TEMP_KEYS)),
                    "humidity": int(_pick(values, HUM_KEYS)),
                    "battery": int(_pick(values, BAT_KEYS)),
                    "codes": list(values.keys()),
                }
            except Exception as exc:
                out["read_error"] = str(exc)[:300]
            diag_path = Path(__file__).with_name("tuya_diag.json")
            diag_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print("ok")
            return 0

        values, _source = _read_values()
        temp = _parse_temp(_pick(values, TEMP_KEYS))
        hum = int(_pick(values, HUM_KEYS))
        bat = int(_pick(values, BAT_KEYS))
        LOG.unlink(missing_ok=True)

        if metric == "temp":
            print(temp)
        elif metric == "humidity":
            print(hum)
        elif metric == "battery":
            print(bat)
        else:
            print(json.dumps({"temp": temp, "humidity": hum, "battery": bat}))
        return 0
    except Exception as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
