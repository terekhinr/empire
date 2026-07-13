#!/usr/bin/env python3
"""Привести HA к стабильному baseline (без go2rtc/CSS-экспериментов).

  venv/bin/python3 tools/ha_stabilize.py           # проверка + мягкие фиксы
  venv/bin/python3 tools/ha_stabilize.py --apply   # применить на HA
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]

TECKIN = {
    "01KVWABNDDHAQ09RB9A3HSV9ZY": "192.168.1.34",
    "01KVWBAEFZTVY274BA6HBCRNQE": "192.168.1.84",
}
GO2RTC_BAD = "127.0.0.1:8554"


def load_env() -> None:
    p = EMPIRE_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def ha_api(method: str, path: str, body: dict | None = None):
    token = os.environ["HA_TOKEN"]
    base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def ssh_cmd(script: str, timeout: int = 60) -> str:
    host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    return subprocess.check_output(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, host, script],
        text=True,
        timeout=timeout,
        stderr=subprocess.STDOUT,
    )


def scp_to_ha(local: Path, remote: str) -> None:
    host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port, str(local), f"{host}:{remote}"],
        check=True,
    )


def issues_from_storage(ce_text: str) -> list[str]:
    issues = []
    if GO2RTC_BAD in ce_text:
        issues.append("generic camera на go2rtc (127.0.0.1:8554)")
    for entry_id, ip in TECKIN.items():
        if entry_id in ce_text and f"rtsp://{ip}" not in ce_text:
            issues.append(f"Teckin {entry_id} не на прямом RTSP {ip}")
    if ce_text.count("lovelace:") > 1:
        issues.append("дублирующий lovelace: в configuration.yaml")
    return issues


def fix_config_entries(tmp_ce: Path) -> bool:
    ce = json.loads(tmp_ce.read_text())
    changed = False
    for e in ce["data"]["entries"]:
        eid = e.get("entry_id")
        if eid not in TECKIN:
            continue
        ip = TECKIN[eid]
        pwd = os.environ.get("TECKIN_PASS", "pass")
        opts = e.setdefault("options", {})
        src = opts.get("stream_source", "")
        if GO2RTC_BAD in src or ip not in src:
            opts.update({
                "stream_source": f"rtsp://{ip}:554/video0_unicast",
                "still_image_url": f"https://{ip}/cgi-bin/currentpic.cgi",
                "username": "root",
                "password": pwd,
                "content_type": "image/jpeg",
                "advanced": {
                    "authentication": "basic",
                    "framerate": 2,
                    "rtsp_transport": "tcp",
                    "verify_ssl": False,
                },
            })
            e["title"] = ip.replace(".", "_")
            changed = True
            print(f"  ✓ Teckin {eid} → прямой RTSP {ip}")
    if changed:
        tmp_ce.write_text(json.dumps(ce, indent=2))
    return changed


def main() -> int:
    load_env()
    if not os.environ.get("HA_TOKEN"):
        sys.exit("HA_TOKEN не задан")

    apply = "--apply" in sys.argv
    print("==> 1) Health check")
    hc = subprocess.run([str(EMPIRE_DIR / "venv/bin/python3"), str(EMPIRE_DIR / "tools/ha_health_check.py")])
    health_rc = hc.returncode

    print("\n==> 2) Проверка конфигов на HA")
    try:
        lovelace = ssh_cmd("grep -c '^lovelace:' /config/configuration.yaml 2>/dev/null || echo 0").strip()
        ce_snip = ssh_cmd("grep -E 'stream_source|8554' /config/.storage/core.config_entries | head -10")
    except subprocess.CalledProcessError as exc:
        print(exc.output or exc)
        return 2

    issues = issues_from_storage(ce_snip)
    if lovelace not in ("0", "1"):
        issues.append(f"lovelace блоков: {lovelace}")
    if int(lovelace or 0) > 1:
        issues.append("дублирующий lovelace:")

    if issues:
        print("  Проблемы:", "; ".join(issues))
    else:
        print("  Конфиг Teckin/lovelace: OK")

    if not apply:
        print("\n(dry-run) Для применения: venv/bin/python3 tools/ha_stabilize.py --apply")
        return health_rc

    print("\n==> 3) Применение baseline")
    changed_ce = False
    tmp = Path(tempfile.gettempdir()) / "ha_ce_stabilize.json"
    host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-P", port,
         f"{host}:/config/.storage/core.config_entries", str(tmp)],
        check=True,
    )
    if fix_config_entries(tmp) or GO2RTC_BAD in tmp.read_text():
        scp_to_ha(tmp, "/config/.storage/core.config_entries")
        changed_ce = True

    scp_to_ha(EMPIRE_DIR / "homeassistant/go2rtc.yaml", "/config/go2rtc.yaml")
    scp_to_ha(EMPIRE_DIR / "homeassistant/dashboards/empire_wall.yaml", "/config/dashboards/empire_wall.yaml")
    print("  ✓ go2rtc.yaml очищен, dashboard обновлён")

    if changed_ce:
        print("  перезапуск HA core…")
        ssh_cmd("ha core restart", timeout=200)

    print("\n==> 4) Teckin flip=1 (аппаратный)")
    py = str(EMPIRE_DIR / "venv/bin/python3")
    for slot in ("1", "2"):
        subprocess.run([py, str(EMPIRE_DIR / "tools/ha_teckin_fix.py"), "--slot", slot, "--flip", "1"], check=False)

    print("\n==> 5) Балкон: fetch key + reload")
    try:
        ha_api("POST", "/api/services/shell_command/balkon_srw_fetch_key", {})
        ha_api("POST", "/api/services/homeassistant/reload_core_config", {})
        for eid in TECKIN:
            ha_api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": eid})
    except Exception as exc:
        print(f"  WARN: {exc}")

    print("\n==> Итог")
    subprocess.run([py, str(EMPIRE_DIR / "tools/ha_health_check.py")])
    print("\nBaseline: прямой RTSP, flip на камере, без go2rtc.")
    print("Балкон/Семён offline — физически: кнопка на датчике.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
