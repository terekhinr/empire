#!/usr/bin/env python3
"""Teckin TC100: диагностика + обновление IP в Generic Camera.

  venv/bin/python3 tools/ha_teckin_fix.py              # проверка
  TECKIN_IP=192.168.1.50 venv/bin/python3 tools/ha_teckin_fix.py --update
  TECKIN2_IP=192.168.1.51 venv/bin/python3 tools/ha_teckin_fix.py --update --slot 2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

EMPIRE_DIR = Path(__file__).resolve().parents[1]

CAMERAS = {
    "1": {
        "entity": "camera.teckin_tc100",
        "default_ip": "192.168.1.34",
        "env_ip": "TECKIN_IP",
        "name": "Teckin TC100",
    },
    "2": {
        "entity": "camera.teckin_tc100_2",
        "default_ip": "192.168.1.84",
        "env_ip": "TECKIN2_IP",
        "name": "Teckin TC100 2",
    },
}


def load_env() -> None:
    env_path = EMPIRE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ha_base() -> str:
    return os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")


def ha_token() -> str:
    token = os.environ.get("HA_TOKEN", "")
    if not token:
        sys.exit("HA_TOKEN не задан (.env)")
    return token


def api(method: str, path: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{ha_base()}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {ha_token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def port_open(ip: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_teckin(ip: str) -> dict:
    return {
        "ip": ip,
        "rtsp_554": port_open(ip, 554),
        "https_443": port_open(ip, 443),
        "ok": port_open(ip, 554) or port_open(ip, 443),
    }


def _ssh_ha(script: str, timeout: int = 30) -> str:
    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    return subprocess.check_output(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, ha_host, script],
        text=True,
        timeout=timeout,
        stderr=subprocess.STDOUT,
    )


def teckin_curl(ip: str, path: str, *, post_data: str | None = None, timeout: int = 45) -> str:
    """HTTP(S) к камере с HA-хоста (LAN 192.168.x.x)."""
    pwd = os.environ.get("TECKIN_PASS", "pass")
    # shell-escape single quotes in password
    pwd_q = pwd.replace("'", "'\"'\"'")
    url = f"https://{ip}/{path.lstrip('/')}"
    if post_data is None:
        cmd = f"curl -sk -u '***REMOVED***' '{url}'"
    else:
        data_q = post_data.replace("'", "'\"'\"'")
        cmd = f"curl -sk -u '***REMOVED***' -X POST -d '{data_q}' '{url}'"
    return _ssh_ha(cmd, timeout=timeout)


def get_image_flip(ip: str) -> int | None:
    import re

    html = teckin_curl(ip, "cgi-bin/status.cgi")
    m = re.search(
        r'<select name="imageFlip"[^>]*>.*?<option value="(\d)"\s+selected',
        html,
        re.S,
    )
    return int(m.group(1)) if m else None


def set_image_flip(ip: str, value: int) -> None:
    if value not in (0, 1, 2, 3):
        raise ValueError("flip value must be 0–3")
    teckin_curl(ip, "cgi-bin/action.cgi?cmd=image-flip", post_data=f"flipValue={value}")
    # flip меняет setconf без рестарта RTSP — перезапускаем поток
    try:
        teckin_curl(ip, "cgi-bin/action.cgi?cmd=rtsp-log-on", timeout=15)
        teckin_curl(ip, "cgi-bin/action.cgi?cmd=rtsp-log-off", timeout=15)
    except subprocess.TimeoutExpired:
        print("  WARN: RTSP restart timeout (flip применён, перезагрузите камеру при необходимости)")


def generic_entries() -> list[dict]:
  return [e for e in api("GET", "/api/config/config_entries/entry") if e.get("domain") == "generic"]


def entry_for_ip(ip: str) -> dict | None:
    slug = ip.replace(".", "_")
    for e in generic_entries():
        if e.get("title") == slug:
            return e
    for e in generic_entries():
        opts = e.get("options") or {}
        if ip in str(opts.get("stream_source", "")):
            return e
    return None


def build_options(ip: str, password: str = "pass") -> dict:
    return {
        "stream_source": f"rtsp://{ip}:554/video0_unicast",
        "still_image_url": f"https://{ip}/cgi-bin/currentpic.cgi",
        "username": "root",
        "password": password,
        "content_type": "image/jpeg",
        "advanced": {
            "authentication": "basic",
            "framerate": 2,
            "rtsp_transport": "tcp",
            "verify_ssl": False,
        },
    }


async def update_entry(entry_id: str, ip: str, password: str = "pass") -> None:
    if websockets is None:
        sys.exit("pip install websockets")
    ws_url = ha_base().replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": ha_token()}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("websocket auth failed")
        await ws.send(
            json.dumps(
                {
                    "id": 1,
                    "type": "config_entries/update",
                    "entry_id": entry_id,
                    "options": build_options(ip, password),
                }
            )
        )
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if not msg.get("success", True):
                    raise RuntimeError(msg.get("error", msg))
                return


def reload_entry(entry_id: str) -> None:
    api("POST", "/api/services/homeassistant/reload_config_entry", {"entry_id": entry_id})


def scan_lan_for_teckin() -> list[str]:
    """Ищем HTTPS/RTSP на 192.168.1.0/24 с HA (исключая известные Ezviz)."""
    ha_host = os.environ.get("HA_SSH", "root@100.80.133.85")
    port = os.environ.get("HA_SSH_PORT", "22222")
    key = os.path.expanduser("~/.ssh/id_ed25519")
    script = (
        "known='56 119'; hits=''; "
        "for i in $(seq 1 254); do "
        "(timeout 0.4 bash -c \"echo >/dev/tcp/192.168.1.$i/443\" 2>/dev/null && "
        "echo $i | grep -qvE \"^(${known// /|})$\" && echo 443:$i) & "
        "(timeout 0.4 bash -c \"echo >/dev/tcp/192.168.1.$i/554\" 2>/dev/null && "
        "echo $i | grep -qvE \"^(${known// /|})$\" && echo 554:$i) & "
        "done; wait"
    )
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-i", key, "-p", port, ha_host, script],
            text=True,
            timeout=120,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    ips: set[str] = set()
    for line in out.splitlines():
        if ":" in line:
            ips.add(line.split(":", 1)[1].strip())
    return sorted(ips)


def diagnose_slot(slot: str) -> int:
    meta = CAMERAS[slot]
    ip = os.environ.get(meta["env_ip"], meta["default_ip"])
    print(f"==> {meta['name']} ({meta['entity']}) @ {ip}")
    probe = probe_teckin(ip)
    print(f"  RTSP 554: {'open' if probe['rtsp_554'] else 'closed'}")
    print(f"  HTTPS 443: {'open' if probe['https_443'] else 'closed'}")
    try:
        state = api("GET", f"/api/states/{meta['entity']}")["state"]
        print(f"  HA state: {state}")
    except urllib.error.HTTPError as exc:
        print(f"  HA entity: missing ({exc.code})")
    entry = entry_for_ip(ip)
    print(f"  generic entry: {entry['entry_id'] if entry else 'not found'}")
    if probe["ok"]:
        print("  OK — камера в сети")
        return 0
    print("  FAIL — HA не достучится до камеры (Host is unreachable в логах)")
    return 1


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=("1", "2"), default="1")
    parser.add_argument("--update", action="store_true", help="обновить IP в generic entry")
    parser.add_argument("--scan", action="store_true", help="скан LAN с HA, подсказать IP")
    parser.add_argument("--flip", type=int, choices=(0, 1, 2, 3), metavar="N",
                        help="аппаратный поворот: 0=выкл 1=flip 2=mirror 3=оба")
    parser.add_argument("--show-flip", action="store_true", help="текущий image flip на камере")
    args = parser.parse_args()

    meta = CAMERAS[args.slot]
    ip = os.environ.get(meta["env_ip"], meta["default_ip"])

    if args.show_flip or args.flip is not None:
        cur = get_image_flip(ip)
        if args.show_flip:
            labels = {0: "выкл", 1: "flip (180°)", 2: "mirror", 3: "flip+mirror"}
            print(f"  imageflip на {ip}: {cur} ({labels.get(cur, '?')})")
        if args.flip is not None:
            print(f"\n==> imageflip {ip}: {cur} → {args.flip}")
            set_image_flip(ip, args.flip)
            new = get_image_flip(ip)
            print(f"  сейчас: {new}")
            entry = entry_for_ip(ip)
            if entry:
                reload_entry(entry["entry_id"])
                print(f"  перезагружен generic entry {entry['entry_id']}")
        return 0

    rc = diagnose_slot(args.slot)

    if args.scan:
        print("\n==> Скан LAN (кроме Ezviz .56/.119)")
        found = scan_lan_for_teckin()
        if found:
            print("  Возможные Teckin IP:", ", ".join(found))
            print("  Обновить: TECKIN_IP=... venv/bin/python3 tools/ha_teckin_fix.py --update")
        else:
            print("  Teckin не найден — камера выключена или SD-hack не поднял Wi‑Fi/RTSP")

    if args.update:
        ip = os.environ.get(meta["env_ip"], "")
        if not ip:
            sys.exit(f"Задайте {meta['env_ip']}=192.168.1.x")
        entry = entry_for_ip(meta["default_ip"]) or entry_for_ip(ip)
        if not entry:
            sys.exit("generic entry не найден — сначала bash deploy/ha_deploy_teckin_tc100.sh")
        pwd = os.environ.get("TECKIN_PASS", "pass")
        print(f"\n==> Обновление entry {entry['entry_id']} → {ip}")
        print("  через HA UI: Настройки → Устройства → Generic → настроить stream URL")
        print(f"  stream: rtsp://{ip}:554/video0_unicast")
        print(f"  still:  https://{ip}/cgi-bin/currentpic.cgi")
        print("  или на VPS: TECKIN_IP=... bash deploy/ha_deploy_teckin_tc100.sh (пересоздать)")
        return 2

    if rc:
        print("\nЧто проверить на камере:")
        print("  1) microSD с hack-files вставлена, питание перезапущено")
        print("  2) wpa_supplicant.conf на карте — Wi‑Fi 2.4 GHz")
        print("  3) В роутере Keenetic — новый IP камеры")
        print("  4) TECKIN_IP=<ip> python3 tools/ha_teckin_fix.py --update")
        print("  Гайд: scripts/teckin-tc100/README.md")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
