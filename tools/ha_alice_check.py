#!/usr/bin/env python3
"""Проверка готовности HA к Алисе (скрипты, свет ванной, Yandex)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

REQUIRED_SCRIPTS = [
    "script.rezhim_noch_vklyuchit",
    "script.rezhim_noch_vyklyuchit",
    "script.rezhim_ushel_vklyuchit",
    "script.rezhim_deti_spiat_vklyuchit",
    "script.rezhim_otpusk_vklyuchit",
]
REQUIRED_LIGHT = "light.empire_vannaya_svet"
RAW_DIMMER = "light.tz3000_mgusv51k_ts0052"


def main() -> int:
    url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not url or not token:
        print("Задайте HA_URL и HA_TOKEN (например из .env)", file=sys.stderr)
        return 2

    req = urllib.request.Request(
        f"{url}/api/states",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            states = {s["entity_id"]: s for s in json.loads(resp.read())}
    except urllib.error.URLError as e:
        print(f"Ошибка HA API: {e}", file=sys.stderr)
        return 1

    ok = True
    print("=== Скрипты режимов ===")
    for eid in REQUIRED_SCRIPTS:
        st = states.get(eid)
        if not st:
            print(f"  MISSING  {eid}")
            ok = False
        else:
            print(f"  OK       {eid}  ({st['attributes'].get('friendly_name', '')})")

    print("\n=== Свет ванной ===")
    if REQUIRED_LIGHT in states:
        print(f"  OK       {REQUIRED_LIGHT}")
    else:
        print(f"  MISSING  {REQUIRED_LIGHT}")
        print("           → скопируйте packages/empire_vannaya_dimmer_fix.yaml, перезагрузите шаблоны")
        ok = False
    if RAW_DIMMER in states:
        print(f"  RAW      {RAW_DIMMER} (в Алису НЕ отдавать)")

    print("\n=== Yandex Smart Home ===")
    req2 = urllib.request.Request(
        f"{url}/api/config/config_entries/entry",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req2, timeout=20) as resp:
        entries = json.loads(resp.read())
    yandex = [e for e in entries if e.get("domain") == "yandex_smart_home"]
    if not yandex:
        print("  MISSING  интеграция yandex_smart_home")
        ok = False
    elif len(yandex) > 1:
        print(f"  WARN     записей интеграции: {len(yandex)} — оставьте одну (Yaha Cloud)")
        for e in yandex:
            print(f"             {e.get('title')}  state={e.get('state')}")
    else:
        e = yandex[0]
        print(f"  OK       {e.get('title')}  state={e.get('state')}")

    print("\n=== Дальше ===")
    print("  1) /config/yandex_smart_home.yaml + строка в configuration.yaml")
    print("  2) Интеграция → Объекты для передачи → «Через YAML»")
    print("  3) Дом с Алисой → обновить устройства Yaha Cloud")
    print("  Гайд: docs/HA_YANDEX_ALICE_SETUP.md")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
