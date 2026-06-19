#!/usr/bin/env python3
"""Туалет: min чувствительность mmWave. Кухня: статус Zbeacon."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def env(name: str, default: str = "") -> str:
    v = os.environ.get(name, default)
    if v:
        return v
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.isfile(env_path):
        for line in open(env_path, encoding="utf-8"):
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return default


def api(method: str, path: str, body: dict | None = None) -> dict | list | str:
    base = env("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    token = env("HA_TOKEN")
    if not token:
        sys.exit("HA_TOKEN не задан")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else ""
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")


def main() -> None:
    sens = "number.tze204_qasjif9e_ts0601_chuvstvitelnost_k_dvizheniiu"
    st = api("GET", f"/api/states/{sens}")
    mn = st["attributes"]["min"]
    mx = st["attributes"]["max"]
    print(f"Туалет чувствительность: было {st['state']} (min={mn}, max={mx})")
    api("POST", "/api/services/number/set_value", {"entity_id": sens, "value": mn})
    st2 = api("GET", f"/api/states/{sens}")
    print(f"Туалет чувствительность: стало {st2['state']}")

    print("\nКухня:")
    for eid in ("light.zbeacon_ts0001", "light.empire_kuhnya_svet", "switch.kuhnya_chainik"):
        s = api("GET", f"/api/states/{eid}")
        note = ""
        if eid == "light.empire_kuhnya_svet":
            note = " (должен совпадать с zbeacon: on=горит)"
        print(f"  {eid}: {s['state']}{note}")

    raw = api("GET", "/api/states/light.zbeacon_ts0001")["state"]
    virt = api("GET", "/api/states/light.empire_kuhnya_svet")["state"]
    if raw == "unavailable":
        print("\n⚠ Zbeacon недоступен — проверь ZHA, питание, роутер Zigbee рядом.")
    elif raw == virt:
        print(f"\n✓ Кухня: zbeacon={raw}, empire={virt} — состояния совпадают.")
    else:
        print(f"\n⚠ Кухня: zbeacon={raw}, empire={virt} — расхождение, нужен template/reload.")


if __name__ == "__main__":
    main()
