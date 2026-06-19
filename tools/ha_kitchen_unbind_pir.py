#!/usr/bin/env python3
"""Отвязать Zbeacon от PIR на живом HA (только API, Tailscale).

Отключает автоматизации «Коридор — движение…» / empire_koridor_pir_*.
Не меняет YAML на диске — для этого deploy/ha_deploy_kitchen.sh (нужен SSH).

  set -a && source .env && set +a
  python3 tools/ha_kitchen_unbind_pir.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

KORIDOR_AUTOMATIONS = [
    "automation.koridor_dvizhenie_svet_vkl",
    "automation.koridor_net_dvizheniia_svet_vykkl",
    "automation.empire_koridor_pir_light_on",
    "automation.empire_koridor_pir_light_off",
]


def api_post(url: str, token: str, path: str, data: dict | None = None) -> list | dict:
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        f"{url}{path}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else []


def get_state(url: str, token: str, eid: str) -> dict | None:
    req = urllib.request.Request(
        f"{url}/api/states/{eid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def main() -> int:
    url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not url or not token:
        print("Нужны HA_URL и HA_TOKEN", file=sys.stderr)
        return 2

    print(f"HA: {url}\n")
    disabled = 0
    for eid in KORIDOR_AUTOMATIONS:
        st = get_state(url, token, eid)
        if not st:
            continue
        if st["state"] == "off":
            print(f"  уже выкл  {eid}")
            continue
        try:
            api_post(url, token, "/api/services/automation/turn_off", {"entity_id": eid})
            print(f"  выкл     {eid}")
            disabled += 1
        except Exception as ex:
            print(f"  ошибка  {eid}: {ex}")

    zbeacon = get_state(url, token, "light.zbeacon_ts0001")
    if zbeacon:
        print(f"\n  Zbeacon: {zbeacon['state']} ({zbeacon['attributes'].get('friendly_name')})")
    print(
        "\nДальше на HA (File editor): обновить packages/empire_motion_pir_koridor.yaml "
        "и /config/yandex_smart_home.yaml из репозитория → Reload automations + yandex_smart_home.reload"
    )
    return 0 if disabled >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
