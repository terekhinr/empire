#!/usr/bin/env python3
"""Poll SRW-TH01: local LAN first, then Tuya Cloud fallback."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tinytuya_pkg"))
import tinytuya  # noqa: E402

DEVICE_ID = "bf86f3c7f53b7bb055f6x2"
# Кандидаты, если UDP-scan пустой (батарейный SRW часто спит).
# НЕ использовать 192.168.1.143 — это Wifi Plug Кухня (localtuya), конфликт IP ломал климат.
# .51 — резерв DHCP под SRW; если DOWN — датчик спит (кнопка 1 сек) или сменил IP.
CANDIDATE_IPS = ("192.168.1.51",)
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
    if isinstance(raw, bool):
        raise ValueError("pairing/config mode")
    val = float(raw)
    return round(val / 10.0, 1) if val > 100 else round(val, 1)


def _valid_sensor_values(values: dict) -> bool:
    if values.get("va_temperature") is True:
        return False
    try:
        temp = _parse_temp(_pick(values, TEMP_KEYS))
    except (TypeError, ValueError):
        return False
    return 5 <= temp <= 55


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
    dev.set_socketTimeout(3)
    dev.set_socketRetryLimit(1)
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


def _localtuya_srw_key() -> tuple[str, str] | None:
    if not LOCALTUYA_STORE.exists():
        return None
    try:
        store = json.loads(LOCALTUYA_STORE.read_text())
        lt = next(e for e in store["data"]["entries"] if e.get("domain") == "localtuya")
        dev = lt["data"].get("devices", {}).get(DEVICE_ID, {})
        key = dev.get("local_key", "")
        if key:
            return key, dev.get("protocol_version") or "3.3"
    except Exception:
        pass
    return None


def _srw_keys() -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if LOCAL.exists():
        try:
            cfg = json.loads(LOCAL.read_text())
            if cfg.get("local_key"):
                keys.append((cfg["local_key"], cfg.get("version") or "3.3"))
        except Exception:
            pass
    lt = _localtuya_srw_key()
    if lt and lt not in keys:
        keys.append(lt)
    return keys


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
            values = _read_values_local({"ip": ip, "local_key": local_key, "version": ver})
            if _valid_sensor_values(values):
                return values
        except Exception:
            continue
    return None


def _candidate_ips() -> list[str]:
    out: list[str] = []
    if LOCAL.exists():
        try:
            saved = (json.loads(LOCAL.read_text()).get("ip") or "").strip()
            if saved and saved not in ("0.0.0.0", "127.0.0.1"):
                out.append(saved)
        except Exception:
            pass
    for ip in CANDIDATE_IPS:
        if ip not in out:
            out.append(ip)
    return out


def _discover_by_probe(keys: list[tuple[str, str]]) -> dict | None:
    for ip in _candidate_ips():
        for key, key_ver in keys:
            if not key:
                continue
            values = _probe_local(ip, key, key_ver)
            if values:
                return {"ip": ip, "local_key": key, "version": key_ver or "3.3", "_values": values}
    return None


def _discover_local_cfg() -> dict | None:
    keys = _srw_keys()

    # Сначала быстрый probe известных IP (батарейный SRW часто не отвечает на UDP-scan).
    probed = _discover_by_probe(keys)
    if probed:
        return probed

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

    for key, key_ver in _srw_keys():
        values = _probe_local(ip, key, key_ver or ver)
        if values:
            return {"ip": ip, "local_key": key, "version": key_ver or ver or "3.3"}

    return {"ip": ip, "version": ver or "3.3", "local_key": None}



def fetch_key_and_probe() -> int:
    """Обновить local_key из Tuya Cloud (если есть .tuya_cloud.json), затем probe."""
    import subprocess
    fetch = Path(__file__).with_name("tuya_srw_fetch_key.py")
    if fetch.exists() and CREDS.exists():
        try:
            r = subprocess.run(["python3", str(fetch)], capture_output=True, text=True, timeout=60)
            print((r.stdout or "")[:300])
            if r.returncode != 0:
                print((r.stderr or "")[:300])
        except Exception as exc:
            print(f"fetch_key err: {exc}")
    return probe_and_save()

def probe_and_save() -> int:
    """Только probe IP из .srw_local / кандидатов — без UDP-scan (быстро)."""
    keys = _srw_keys()
    if not keys:
        return _fail("no local_key (iot.tuya.com / .srw_local.json)")
    found = _discover_by_probe(keys)
    if not found:
        return _fail("SRW спит — короткое нажатие кнопки на датчике (1 сек)")
    values = found.pop("_values", None)
    if not values:
        return _fail("SRW в пейринге — короткое нажатие, не зажимать")
    LOCAL.write_text(
        json.dumps({k: found[k] for k in ("ip", "local_key", "version") if k in found},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LOG.unlink(missing_ok=True)
    payload = {
        "ip": found["ip"],
        "version": found.get("version"),
        "temp": _parse_temp(_pick(values, TEMP_KEYS)),
        "humidity": int(_pick(values, HUM_KEYS)),
        "battery": int(_pick(values, BAT_KEYS)),
        "codes": list(values.keys()),
    }
    Path(__file__).with_name("tuya_discover_last.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload))
    return 0


def discover_and_save() -> int:
    # Сначала обновить local_key из Tuya Cloud (если есть .tuya_cloud.json).
    return fetch_key_and_probe()



def _unused_discover_full() -> int:
    found = _discover_local_cfg()
    if not found:
        return _fail("SRW-TH01 not found in LAN scan (нажмите кнопку на датчике)")
    if not found.get("local_key"):
        return _fail(f"SRW @ {found.get('ip')} found, local_key missing (renew iot.tuya.com or tinytuya wizard)")
    values = found.pop("_values", None) or _probe_local(found["ip"], found["local_key"], found.get("version"))
    if not values:
        return _fail("SRW в пейринге или спит — короткое нажатие, не зажимать")
    LOCAL.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.unlink(missing_ok=True)
    payload = {
        "ip": found["ip"],
        "version": found.get("version"),
        "temp": _parse_temp(_pick(values, TEMP_KEYS)),
        "humidity": int(_pick(values, HUM_KEYS)),
        "battery": int(_pick(values, BAT_KEYS)),
        "codes": list(values.keys()),
        "raw": values,
    }
    Path(__file__).with_name("tuya_discover_last.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload))
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
        if metric == "probe":
            return probe_and_save()
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
