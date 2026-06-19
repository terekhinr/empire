#!/usr/bin/env python3
"""Диагностика ванной на живом HA (API). Запуск: source .env && python3 tools/ha_vannaya_diagnose.py"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

ENTITIES = [
    "binary_sensor.sonoff_snzb_06p",
    "binary_sensor.empire_vannaya_dim_night",
    "light.tz3000_mgusv51k_ts0052",
    "light.empire_vannaya_svet",
    "script.empire_vannaya_svet_pri_presence",
    "script.empire_vannaya_raw_on_level",
    "automation.vannaia_prisutstvie_svet_den_noch",
    "automation.vannaia_net_prisutstviia_vykl_svet",
]


def get_state(url: str, token: str, eid: str) -> dict | None:
    req = urllib.request.Request(
        f"{url}/api/states/{eid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def main() -> int:
    url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not url or not token:
        print("Нужны HA_URL и HA_TOKEN", file=sys.stderr)
        return 2

    print(f"HA: {url}\n")
    problems = []

    for eid in ENTITIES:
        st = get_state(url, token, eid)
        if not st:
            print(f"  MISSING   {eid}")
            if "script.empire_vannaya_raw" in eid:
                problems.append("Старый script raw_on_level отсутствует — OK если пакет обновлён")
            else:
                problems.append(f"Нет сущности {eid}")
            continue
        name = st["attributes"].get("friendly_name", "")
        print(f"  {st['state']:12} {eid}  ({name})")
        if eid.startswith("script.") and st["state"] == "unavailable":
            problems.append(f"{eid} unavailable — на HA старый YAML, обновите packages")
        if eid.startswith("automation.") and st["state"] == "off":
            problems.append(f"{eid} выключена в HA")

    raw = get_state(url, token, "light.tz3000_mgusv51k_ts0052")
    occ = get_state(url, token, "binary_sensor.sonoff_snzb_06p")
    if raw and occ:
        print("\nСводка:")
        print(f"  Датчик присутствия: {occ['state']}")
        print(f"  Диммер в HA:         {raw['state']}  brightness={raw['attributes'].get('brightness')}")
        if raw["state"] == "on" and occ["state"] == "off":
            print("  → Свет в HA «on», людей нет — должна сработать автоматизация выкл через 30 с")

    if problems:
        print("\nПроблемы:")
        for p in problems:
            print(f"  - {p}")
        print("\nДеплой: bash deploy/ha_deploy_vannaya.sh (SSH на armbian)")
        print("Или вручную в File editor скопировать packages/*.yaml из репозитория")
        return 1

    print("\nСущности на месте. Если свет не реагирует — обновите packages на HA и Reload automations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
