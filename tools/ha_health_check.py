#!/usr/bin/env python3
"""Проверка здоровья Empire HA (read-only).

  venv/bin/python3 tools/ha_health_check.py
  venv/bin/python3 tools/ha_health_check.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]

CHECKS = {
    "cameras": [
        ("camera.teckin_tc100", "Кухня", {"idle", "recording", "streaming"}),
        ("camera.teckin_tc100_2", "Детская", {"idle", "recording", "streaming"}),
        ("camera.ezviz_prihozhaya", "Прихожая", {"idle", "recording", "streaming"}),
        ("camera.ezviz_podezd", "Подъезд", {"idle", "recording", "streaming"}),
    ],
    "climate": [
        ("sensor.sber_th_temperatura", "Кухня t°", None),
        ("sensor.spalnya_temperatura", "Спальня t°", None),
        ("sensor.balkon_temperatura", "Балкон t°", None),
        ("sensor.ewelink_ck_tlsr8656_ss5_01_7014_temperatura_2", "Семён t°", None),
        ("sensor.ewelink_ck_tlsr8656_ss5_01_7014_temperatura", "Детская t°", None),
    ],
    "safety": [
        ("binary_sensor.hobeian_zg_222z", "Протечка ванная", None),
        ("binary_sensor.balkon_datchik_gaza", "Газ балкон", None),
    ],
}


def load_env() -> None:
    p = EMPIRE_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def states() -> dict[str, dict]:
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        sys.exit("HA_TOKEN не задан")
    base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    req = urllib.request.Request(
        f"{base}/api/states",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {s["entity_id"]: s for s in json.loads(resp.read())}


def check_entity(all_states: dict[str, dict], eid: str, label: str, ok_states: set[str] | None) -> dict:
    st = all_states.get(eid, {})
    state = st.get("state", "missing")
    if state == "missing":
        return {"id": eid, "label": label, "state": state, "ok": False, "note": "entity отсутствует"}
    if ok_states is not None:
        ok = state in ok_states
    else:
        ok = state not in ("unavailable", "unknown", "missing", "none", "")
    note = ""
    if not ok and "balkon" in eid:
        note = "SRW спит/offline — кнопка на датчике или LocalTuya"
    if not ok and "ewelink" in eid and "7014_temperatura" in eid and not eid.endswith("_2"):
        note = "Zigbee offline — кнопка на датчике 5–10 с"
    return {"id": eid, "label": label, "state": state, "ok": ok, "note": note}


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        all_states = states()
    except urllib.error.URLError as exc:
        print(f"FAIL: HA недоступен — {exc}")
        return 2

    report: dict[str, list] = {}
    bad = 0
    for group, items in CHECKS.items():
        report[group] = []
        for eid, label, ok_states in items:
            row = check_entity(all_states, eid, label, ok_states)
            report[group].append(row)
            if not row["ok"]:
                bad += 1

    if args.json:
        print(json.dumps({"ok": bad == 0, "issues": bad, "checks": report}, ensure_ascii=False, indent=2))
        return 0 if bad == 0 else 1

    print("==> Empire HA health")
    for group, rows in report.items():
        print(f"\n[{group}]")
        for row in rows:
            mark = "OK" if row["ok"] else "FAIL"
            line = f"  {mark:4} {row['label']}: {row['state']}"
            if row.get("note"):
                line += f" — {row['note']}"
            print(line)
    print(f"\nИтого: {bad} проблем" if bad else "\nВсё OK")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
