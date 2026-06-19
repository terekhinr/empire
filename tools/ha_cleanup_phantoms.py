#!/usr/bin/env python3
"""Убрать офлайн-устройства и спрятать служебные сущности из меню HA."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.request

IEEE_KITCHEN_OFFLINE = "a4:c1:38:8f:db:11:a7:14"

HIDE_ENTITY_PREFIXES = (
    "button.",
    "select.",
    "update.",
    "conversation.",
    "device_tracker.",
    "notify.",
    "tts.",
    "person.",
)

HIDE_ENTITY_EXACT = {
    "light.zbeacon_ts0001",
    "light.zbeacon_ts0001_2",
    "light.tz3000_mgusv51k_ts0052",
    "light.hobeian_zg_301z",
    "script.empire_kuhnya_zbeacon_set",
    "script.empire_kuhnya_zbeacon_physical_on",
    "script.empire_kuhnya_zbeacon_physical_off",
    "script.empire_prihozhaya_zbeacon_set",
    "script.empire_prihozhaya_zbeacon_on",
    "script.empire_prihozhaya_zbeacon_off",
    "script.empire_tualet_hobeian_set",
    "script.svet_kuhnya_vkl",
    "script.svet_kuhnya_vyk",
    "script.svet_tualet_vkl",
    "script.svet_tualet_vyk",
    "script.svet_vannaya_vkl",
    "script.svet_vannaya_vyk",
    "script.svet_prihozhaya_vkl",
    "script.svet_prihozhaya_vyk",
    "group.tekhnika_otpusk",
}

HIDE_ENTITY_SUFFIXES = (
    "_identifikatsiia",
    "_identifikatsiia_2",
    "_identifikatsiia_3",
    "_povedenie_pri_zapuske",
    "_obnovlenie_proshivki",
    "_pre_release",
    "_led",
    "_pulse",
    "_samodiagnostika",
)

REMOVE_ENTITY_SUBSTR = (
    "zbeacon_ts0001_3",
    "qasjif9e",
    "tualet_tze204",
    "empire_tualet_presence",
)

REMOVE_AUTOMATIONS = {
    "automation.dvizhenie_svet_100_den_20_noch",
    "automation.net_dvizheniia_vykliuchit_svet",
    "automation.smena_rezhima_noch_podstroit_iarkost",
    "automation.vannaia_smena_rezhima_noch_iarkost",
}

REMOVE_SCRIPTS = {
    "script.empire_vannaya_raw_on_level",
    "script.empire_vannaya_svet_pri_presence",
}

HIDE_ADDON_SWITCHES = {
    "switch.esphome_device_builder",
    "switch.file_editor",
    "switch.get_hacs",
    "switch.home_assistant_google_drive_backup",
    "switch.tailscale",
    "switch.terminal_ssh",
}

try:
    import websockets
except ImportError:
    sys.exit("pip install websockets")


def env(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    p = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def api(method: str, path: str, body: dict | None = None):
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


async def ws_call(ws, msg_id: int, msg_type: str, **kwargs) -> dict:
    await ws.send(json.dumps({"id": msg_id, "type": msg_type, **kwargs}))
    while True:
        r = json.loads(await ws.recv())
        if r.get("id") == msg_id:
            if not r.get("success", True):
                raise RuntimeError(r.get("error", r))
            return r


def should_hide(eid: str) -> bool:
    if eid in HIDE_ENTITY_EXACT or eid in HIDE_ADDON_SWITCHES:
        return True
    dom = eid.split(".", 1)[0]
    if dom in HIDE_ENTITY_PREFIXES:
        return True
    return any(eid.endswith(s) or s in eid for s in HIDE_ENTITY_SUFFIXES)


def should_remove(eid: str) -> bool:
    if eid in REMOVE_AUTOMATIONS or eid in REMOVE_SCRIPTS:
        return True
    return any(s in eid for s in REMOVE_ENTITY_SUBSTR)


async def main() -> None:
    base = env("HA_URL") or "http://127.0.0.1:8123"
    token = env("HA_TOKEN")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"

    print("1) zha/remove offline kitchen switch", IEEE_KITCHEN_OFFLINE)
    try:
        api("POST", "/api/services/zha/remove", {"ieee": IEEE_KITCHEN_OFFLINE})
    except Exception as ex:
        print("   zha/remove:", ex)
    time.sleep(2)

    hidden = removed = renamed = 0
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            sys.exit("auth failed")

        mid = 1
        dr = (await ws_call(ws, mid, "config/device_registry/list")).get("result", [])
        mid += 1

        for dev in dr:
            ids = json.dumps(dev.get("identifiers", [])).lower()
            if IEEE_KITCHEN_OFFLINE in ids:
                print("2) remove device", dev.get("name"), dev.get("id"))
                await ws_call(ws, mid, "config/device_registry/remove", device_id=dev.get("id"))
                mid += 1

        er = (await ws_call(ws, mid, "config/entity_registry/list")).get("result", [])
        mid += 1

        for ent in er:
            eid = ent.get("entity_id", "")
            if should_remove(eid):
                print("remove", eid)
                await ws_call(ws, mid, "config/entity_registry/remove", entity_id=eid)
                mid += 1
                removed += 1
                continue
            if ent.get("hidden"):
                continue
            if should_hide(eid):
                await ws_call(
                    ws,
                    mid,
                    "config/entity_registry/update",
                    entity_id=eid,
                    hidden_by="user",
                )
                mid += 1
                hidden += 1

        # rename active kitchen switch
        for dev in dr:
            ids = json.dumps(dev.get("identifiers", [])).lower()
            if "a4:c1:38:98:1b:6d:43:22" in ids:
                await ws_call(
                    ws,
                    mid,
                    "config/device_registry/update",
                    device_id=dev.get("id"),
                    name_by_user="Кухня выключатель",
                )
                mid += 1
                renamed += 1
                print("rename device → Кухня выключатель")

    print(f"done: hidden={hidden}, removed={removed}, renamed={renamed}")
    api("POST", "/api/services/automation/reload", {})
    api("POST", "/api/services/script/reload", {})


if __name__ == "__main__":
    asyncio.run(main())
