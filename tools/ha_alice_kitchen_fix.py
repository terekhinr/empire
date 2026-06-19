#!/usr/bin/env python3
"""Алиса ↔ кухня: деплой, сброс Yaha Cloud, тест реле."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_ID = "01KRZWQPJBMBDSE4GGXWKW039M"
DEPLOY = [
    (ROOT / "homeassistant/yandex_smart_home.yaml", "/homeassistant/yandex_smart_home.yaml"),
    (ROOT / "homeassistant/packages/empire_kuhnya_zbeacon.yaml", "/homeassistant/packages/empire_kuhnya_zbeacon.yaml"),
    (ROOT / "homeassistant/packages/empire_alice_scripts.yaml", "/homeassistant/packages/empire_alice_scripts.yaml"),
]


def env(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    dot = ROOT / ".env"
    if dot.is_file():
        for line in dot.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def api(method: str, path: str, body: dict | None = None, timeout: int = 90):
    base = env("HA_URL").rstrip("/")
    token = env("HA_TOKEN")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def scp(local: Path, remote: str) -> None:
    host = env("HA_SSH") or "root@100.80.133.85"
    port = env("HA_SSH_PORT") or "22222"
    key = env("HA_SSH_KEY") or str(Path.home() / ".ssh/id_ed25519")
    subprocess.run(["scp", "-P", port, "-i", key, str(local), f"{host}:{remote}"], check=True)


def reset_cloud_token() -> None:
    host = env("HA_SSH") or "root@100.80.133.85"
    port = env("HA_SSH_PORT") or "22222"
    key = env("HA_SSH_KEY") or str(Path.home() / ".ssh/id_ed25519")
    local = Path("/tmp/ha_ce_alice_kitchen.json")
    subprocess.run(
        ["scp", "-P", port, "-i", key, f"{host}:/homeassistant/.storage/core.config_entries", str(local)],
        check=True,
    )
    data = json.loads(local.read_text(encoding="utf-8"))
    entry = next(e for e in data["data"]["entries"] if e.get("domain") == "yandex_smart_home")
    entry.setdefault("data", {})["linked_platforms"] = ["yandex"]
    opts = dict(entry.get("options") or {})
    opts["filter_source"] = "yaml"
    entry["options"] = opts
    ci = entry["data"]["cloud_instance"]
    req = urllib.request.Request(
        f"https://yaha-cloud.ru/api/home_assistant/v1/instance/{ci['id']}/reset-connection-token",
        data=b"",
        headers={"Authorization": f"Bearer {ci['token']}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        ci["token"] = json.loads(resp.read())["connection_token"]
    local.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(
        ["scp", "-P", port, "-i", key, str(local), f"{host}:/homeassistant/.storage/core.config_entries"],
        check=True,
    )
    print("Yaha Cloud token обновлён")


def cycle_kitchen(n: int = 4) -> None:
    for i in range(1, n + 1):
        for want, label in ((False, "off"), (True, "on")):
            api("POST", "/api/services/script/empire_kuhnya_zbeacon_set", {"want_on": want}, timeout=120)
            time.sleep(8)
            st = api("GET", "/api/states/light.zbeacon_ts0001")["state"]
            ok = (st == "on") == want
            print(f"  цикл {i} {label}: zbeacon={st} {'OK' if ok else 'FAIL'}")
            if not ok:
                return


def main() -> int:
    print("1) deploy")
    for local, remote in DEPLOY:
        scp(local, remote)
        print(f"   {local.name}")

    print("2) Yaha token + reload")
    try:
        reset_cloud_token()
    except Exception as ex:
        print(f"   token skip: {ex}")

    for svc in ("script/reload", "template/reload", "automation/reload"):
        try:
            api("POST", f"/api/services/{svc}")
        except Exception:
            pass
    api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": ENTRY_ID})
    time.sleep(5)

    entries = api("GET", "/api/config/config_entries/entry")
    yx = next(e for e in entries if e.get("domain") == "yandex_smart_home")
    print(f"3) yandex state: {yx.get('state')}")

    diag = api("GET", f"/api/diagnostics/config_entry/{ENTRY_ID}")
    devs = diag.get("data", {}).get("devices", {})
    print("4) Алиса видит:", devs.get("light.empire_kuhnya_svet", {}).get("description"))

    print("5) тест Zbeacon")
    cycle_kitchen(3)
    print("Готово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
