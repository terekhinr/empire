#!/usr/bin/env python3
"""Мониторинг Flint 2: podkop, zapret, Amnezia, Transmission, Samba. Автопочинка.

Доступ к роутеру:
  1) reverse SSH с VPS: ssh -p 6223 root@127.0.0.1
  2) через HA Tailscale: ssh root@100.80.133.85 → ssh root@192.168.1.1

Лог: /var/log/empire/router-watchdog.log
State: /var/log/empire/router-state.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
STATE_PATH = Path(os.getenv("EMPIRE_ROUTER_STATE", str(LOG_DIR / "router-state.json")))
LOG_PATH = LOG_DIR / "router-watchdog.log"

FLINT = os.getenv("EMPIRE_FLINT_HOST", "192.168.1.1")
HA_SSH = os.getenv("EMPIRE_HA_SSH", "root@100.80.133.85")
REV_SSH = ["ssh", "-p", "6223", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new", "root@127.0.0.1"]
FIX_SCRIPT = os.getenv("EMPIRE_FLINT_FIX_URL", "http://127.0.0.1:8789/13-fix-all.sh")

REMOTE_CHECKS = r"""
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:/opt/bin:/opt/sbin:$PATH"
echo "=== hostname ==="
uci -q get system.@system[0].hostname 2>/dev/null || hostname
echo "=== podkop ==="
if pgrep -af 'sing-box|singbox' 2>/dev/null | grep -qv pgrep; then
  echo "podkop: RUNNING"
  pgrep -af 'sing-box|singbox' 2>/dev/null | grep -v pgrep | head -1
else
  /etc/init.d/podkop status 2>&1 | head -1
  echo "podkop: NOT_RUNNING"
fi
echo "=== zapret ==="
if [ -x /etc/init.d/zapret2 ]; then /etc/init.d/zapret2 status 2>&1 | head -1; fi
if [ -x /etc/init.d/zapret ]; then /etc/init.d/zapret status 2>&1 | head -1; fi
pgrep -af 'nfqws|nfqws2' 2>/dev/null | grep -v pgrep | head -1 || echo "nfqws: NO"
echo "=== amnezia ==="
awg show awg0 2>/dev/null | grep -E 'handshake|latest' | head -2 || echo "awg0: NO"
echo "=== transmission ==="
if pgrep -x transmission-daemon >/dev/null 2>&1 || pgrep -af transmission-daemon | grep -v pgrep >/dev/null 2>&1; then
  echo "transmission: RUNNING"
else
  /etc/init.d/transmission status 2>&1 | head -1
  echo "transmission: NO"
fi
echo "=== samba ==="
/etc/init.d/samba4 status 2>&1 | head -1
echo "=== usb ==="
mountpoint -q /mnt/usb 2>/dev/null && echo "usb: MOUNTED" || echo "usb: NOT_MOUNTED"
echo "=== dns ==="
/etc/init.d/dnsmasq status 2>&1 | head -1 || /etc/init.d/dnsmasq-full status 2>&1 | head -1
echo "=== youtube ==="
curl -sI -m 8 https://www.youtube.com/generate_204 2>/dev/null | head -1 || echo "youtube: FAIL"
"""


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(st: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cmd(cmd: list[str], *, timeout: int = 45) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, str(exc)


def ssh_flint_via_reverse(remote_cmd: str) -> tuple[bool, str]:
    cmd = REV_SSH + [remote_cmd]
    code, out = run_cmd(cmd, timeout=60)
    return code == 0 and "=== hostname ===" in out, out


def ssh_flint_via_ha(remote_cmd: str) -> tuple[bool, str]:
    inner = remote_cmd.replace("'", "'\"'\"'")
    hop = f"ssh -o BatchMode=yes -o ConnectTimeout=12 root@{FLINT} '{inner}'"
    code, out = run_cmd(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HA_SSH, hop], timeout=90)
    return code == 0 and "=== hostname ===" in out, out


def fetch_router_status() -> tuple[str | None, str]:
    """Returns (channel, raw_output). channel: reverse|ha|None"""
    for channel, fn in (("reverse", ssh_flint_via_reverse), ("ha", ssh_flint_via_ha)):
        ok, out = fn(REMOTE_CHECKS)
        if ok:
            return channel, out
        log(f"WARN: {channel} failed: {out[-200:]}")
    return None, ""


def parse_status(raw: str) -> dict:
    checks: dict[str, dict] = {}
    section = "general"

    def set_check(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = {"ok": ok, "detail": (detail or "")[:200]}

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("=== ") and line.endswith(" ==="):
            section = line.strip("= ").lower().split()[0]
            continue
        low = line.lower()
        if section == "podkop":
            if "not running" in low or "inactive" in low or low.strip() == "stopped":
                set_check("podkop", False, line)
            elif "running" in low or "started" in low:
                set_check("podkop", True, line)
            elif "sing-box" in low or "singbox" in low:
                set_check("sing-box", True, line[:120])
        elif section == "zapret":
            if "not running" in low or "inactive" in low:
                set_check("zapret", False, line)
            elif "running" in low or "started" in low:
                set_check("zapret", True, line)
            elif "nfqws" in low and "no" not in low:
                set_check("nfqws", True, line)
            elif line.startswith("nfqws:"):
                set_check("nfqws", "no" not in low, line)
        elif section == "amnezia":
            if "handshake" in low or "latest" in low:
                set_check("awg0", True, line)
            elif "awg0: no" in low:
                set_check("awg0", False, line)
        elif section == "transmission":
            if "running" in low or line.startswith("transmission: RUNNING"):
                set_check("transmission", True, line)
            elif line.startswith("transmission: NO"):
                set_check("transmission", False, line)
        elif section == "samba":
            if "not running" in low or "inactive" in low:
                set_check("samba", False, line)
            elif "running" in low or "started" in low:
                set_check("samba", True, line)
        elif section == "usb":
            if line.startswith("usb:"):
                set_check("usb", "mounted" in low, line)
        elif section == "dns":
            if "not running" in low or "inactive" in low:
                set_check("dns", False, line)
            elif "running" in low or "started" in low:
                set_check("dns", True, line)
        elif section == "youtube":
            if line.startswith("HTTP/"):
                set_check("youtube", "204" in line or "200" in line, line)
            elif "youtube: fail" in low:
                set_check("youtube", False, line)

    # sing-box жив, если процесс найден; иначе — полагаемся на podkop+youtube
    if checks.get("sing-box", {}).get("ok") and not checks.get("podkop", {}).get("ok"):
        checks["podkop"] = {"ok": True, "detail": "sing-box process alive"}
    if checks.get("podkop", {}).get("ok") and checks.get("youtube", {}).get("ok"):
        checks.setdefault("sing-box", {"ok": True, "detail": "podkop+youtube ok"})

    for key in ("podkop", "zapret", "nfqws", "transmission", "samba", "usb", "dns", "youtube"):
        checks.setdefault(key, {"ok": False, "detail": "не проверено"})

    # Критичные для all_ok — без false-positive по имени процесса
    critical = ("podkop", "transmission", "usb", "youtube")
    all_ok = all(checks.get(k, {}).get("ok") for k in critical)
    return {"checks": checks, "all_ok": all_ok}


def remediate(channel: str, st: dict, failed: list[str]) -> list[str]:
    actions: list[str] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rem = st.setdefault("remediation", {})
    if rem.get("day") != today:
        rem.clear()
        rem["day"] = today

    def ssh(cmd: str) -> tuple[int, str]:
        if channel == "reverse":
            return run_cmd(REV_SSH + [cmd], timeout=120)
        inner = cmd.replace("'", "'\"'\"'")
        hop = f"ssh -o BatchMode=yes root@{FLINT} '{inner}'"
        return run_cmd(["ssh", "-o", "BatchMode=yes", HA_SSH, hop], timeout=150)

    # Только точечные restart по факту сломанных checks
    checks = list(failed)
    fix_map = {
        "podkop": ("/etc/init.d/podkop restart 2>&1 | tail -3", 2),
        "youtube": ("/etc/init.d/podkop restart 2>&1 | tail -3", 2),
        "zapret": ("/etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null; echo zapret-ok", 2),
        "nfqws": ("/etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null; echo nfqws-ok", 2),
        "transmission": (
            "uci set transmission.transmission.enabled=1 2>/dev/null; "
            "uci set transmission.@transmission[0].enabled=1 2>/dev/null; uci commit transmission 2>/dev/null; "
            "/etc/init.d/transmission enable 2>/dev/null; /etc/init.d/transmission restart 2>&1 | tail -3",
            2,
        ),
        "samba": ("/etc/init.d/samba4 restart 2>&1 | tail -2", 1),
        "awg0": (
            "awg show awg0 >/dev/null 2>&1 || ("
            "/etc/init.d/amnezia-split restart 2>/dev/null || "
            "sh /etc/amnezia/start-split.sh 2>/dev/null || "
            "(awg-quick down awg0 2>/dev/null; awg-quick up awg0 2>/dev/null)"
            "); echo awg-ok",
            1,
        ),
        "usb": (
            "mkdir -p /mnt/usb; mount /mnt/usb 2>/dev/null || mount -a 2>/dev/null; "
            "mountpoint -q /mnt/usb && echo usb-ok || echo usb-fail",
            2,
        ),
    }
    for name in checks:
        if name not in fix_map:
            continue
        cmd, limit = fix_map[name]
        key = f"fix_{name}"
        if rem.get(key, 0) >= limit:
            continue
        log(f"REMEDIATE: {name}")
        code, out = ssh(cmd)
        rem[key] = rem.get(key, 0) + 1
        actions.append(f"fix {name} (rc={code})")
        log(f"  {out[-300:]}")

    critical_failed = [n for n in ("podkop", "usb", "youtube") if n in checks]
    if critical_failed and rem.get("fix_all", 0) < 1:
        log("REMEDIATE: 13-fix-all.sh (критичные сбои)")
        fix_cmd = f"curl -fsSL {FIX_SCRIPT} 2>/dev/null | sh 2>&1 | tail -8"
        code, out = ssh(fix_cmd)
        rem["fix_all"] = 1
        actions.append(f"fix-all (rc={code})")
        log(f"  {out[-500:]}")

    save_state(st)
    return actions


def build_summary(channel: str | None, parsed: dict, actions: list[str]) -> str:
    lines = [f"🏠 Flint · {channel or 'недоступен'}"]
    if not channel:
        lines.append("❌ роутер не отвечает (reverse SSH и HA)")
        return "\n".join(lines)
    icons = []
    for name, info in parsed.get("checks", {}).items():
        icon = "✅" if info.get("ok") else "❌"
        icons.append(f"{icon} {name}")
    lines.append(" · ".join(icons[:8]))
    if len(icons) > 8:
        lines.append(" · ".join(icons[8:]))
    bad = [k for k, v in parsed.get("checks", {}).items() if not v.get("ok")]
    if bad:
        lines.append(f"⚠ проблемы: {', '.join(bad)}")
    if actions:
        lines.append("🔧 " + "; ".join(actions[:4]))
    return "\n".join(lines)


def main() -> int:
    check_only = "--check-only" in sys.argv
    no_fix = os.getenv("EMPIRE_ROUTER_NO_FIX", "") == "1" or "--no-fix" in sys.argv

    st = load_state()
    st["last_run"] = datetime.now(timezone.utc).isoformat()
    channel, raw = fetch_router_status()
    parsed = parse_status(raw) if raw else {"checks": {}, "all_ok": False}
    actions: list[str] = []

    if channel and not parsed.get("all_ok") and not no_fix and not check_only:
        failed = [k for k, v in parsed.get("checks", {}).items() if not v.get("ok")]
        actions = remediate(channel, st, failed)
        # re-check after fix
        time.sleep(8)
        channel2, raw2 = fetch_router_status()
        if channel2 and raw2:
            channel, parsed = channel2, parse_status(raw2)

    summary = build_summary(channel, parsed, actions)
    st["last_channel"] = channel
    st["last_summary"] = summary
    st["last_all_ok"] = parsed.get("all_ok", False)
    st["last_checks"] = parsed.get("checks", {})
    st["last_actions"] = actions
    save_state(st)
    log(f"done channel={channel} all_ok={parsed.get('all_ok')} actions={len(actions)}")

    if os.getenv("EMPIRE_ROUTER_PRINT_SUMMARY") == "1":
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
