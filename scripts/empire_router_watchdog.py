#!/usr/bin/env python3
"""Мониторинг Flint 2: podkop, zapret, Amnezia, Transmission, Samba. Автопочинка.

Логика стабильности (не «сжёг лимит утром — день мёртв»):
  • чиним только подтверждённые сбои (не «не проверено» / таймаут проверки)
  • cooldown между одинаковыми фиксами + эскалация soft → fix-all
  • после успеха сбрасываем серию неудач — днём снова можно чинить
  • суточный потолок высокий (страховка от шторма), не основной тормоз

Доступ к роутеру:
  1) reverse SSH с VPS: ssh -p 6223 root@127.0.0.1
  2) через HA Tailscale: ssh root@100.80.133.85 → ssh root@192.168.1.1

Лог: /var/log/empire/router-watchdog.log
State: /var/log/empire/router-state.json
"""
from __future__ import annotations

import json
import os
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
REV_SSH = [
    "ssh",
    "-p",
    "6223",
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "StrictHostKeyChecking=accept-new",
    "root@127.0.0.1",
]
FIX_SCRIPT = os.getenv("EMPIRE_FLINT_FIX_URL", "http://127.0.0.1:8789/13-fix-all.sh")

# Секунды между повторными точечными фиксами одного компонента
SOFT_COOLDOWN_SEC = int(os.getenv("EMPIRE_ROUTER_SOFT_COOLDOWN", "1200"))  # 20 мин
# После N неудачных soft-фиксов подряд — полный fix-all
ESCALATE_AFTER = int(os.getenv("EMPIRE_ROUTER_ESCALATE_AFTER", "2"))
# Пауза между полными fix-all
FIXALL_COOLDOWN_SEC = int(os.getenv("EMPIRE_ROUTER_FIXALL_COOLDOWN", "7200"))  # 2 ч
# Страховка от шторма (не основной тормоз)
DAILY_SOFT_CAP = int(os.getenv("EMPIRE_ROUTER_DAILY_SOFT_CAP", "24"))
DAILY_FIXALL_CAP = int(os.getenv("EMPIRE_ROUTER_DAILY_FIXALL_CAP", "6"))

# all_ok: без этого дом/AI/обход реально сломаны. USB — отдельно (часто снят).
# EMPIRE_SKIP_AMNEZIA_PEER=1 — RKN блок IP: awg0 не критичен до нового VPS.
_SKIP_AWG = os.getenv("EMPIRE_SKIP_AMNEZIA_PEER", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
CRITICAL = tuple(
    x
    for x in ("podkop", "youtube", "telegram", "ai", "dns", "awg0", "selfheal")
    if not (_SKIP_AWG and x == "awg0")
)
# Чиним при подтверждённом fail
REMEDIABLE = tuple(
    x
    for x in (
        "podkop",
        "youtube",
        "zapret",
        "nfqws",
        "awg0",
        "transmission",
        "samba",
        "usb",
        "dns",
        "telegram",
        "torrents",
        "ai",
        "selfheal",
        "cron",
        "urltest",
    )
    if not (_SKIP_AWG and x == "awg0")
)

AWG_MAX_AGE_SEC = int(os.getenv("EMPIRE_AWG_MAX_AGE", "180"))

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
if ! awg show awg0 >/dev/null 2>&1 && ! wg show awg0 >/dev/null 2>&1; then
  echo "awg0: NO"
else
  hs=$(awg show awg0 2>/dev/null | grep -i 'latest handshake' | head -1)
  [ -z "$hs" ] && hs=$(wg show awg0 2>/dev/null | grep -i 'latest handshake' | head -1)
  echo "$hs"
  if echo "$hs" | grep -qi 'never'; then
    echo "awg0: STALE age=never"
  else
    age=0
    d=$(echo "$hs" | sed -n 's/.*\([0-9][0-9]*\) day.*/\1/p')
    h=$(echo "$hs" | sed -n 's/.*\([0-9][0-9]*\) hour.*/\1/p')
    m=$(echo "$hs" | sed -n 's/.*\([0-9][0-9]*\) minute.*/\1/p')
    s=$(echo "$hs" | sed -n 's/.*\([0-9][0-9]*\) second.*/\1/p')
    [ -n "$d" ] && age=$((age + d * 86400))
    [ -n "$h" ] && age=$((age + h * 3600))
    [ -n "$m" ] && age=$((age + m * 60))
    [ -n "$s" ] && age=$((age + s))
    if [ "$age" -gt 180 ]; then
      echo "awg0: STALE age=${age}s"
    else
      code=$(curl --interface awg0 -4 -s -o /dev/null -w '%{http_code}' \
        --connect-timeout 8 --max-time 12 https://1.1.1.1/ 2>/dev/null || echo 000)
      case "$code" in
        200|301|302) echo "awg0: OK age=${age}s probe=$code" ;;
        *) echo "awg0: DEAD_PROBE age=${age}s probe=$code" ;;
      esac
    fi
  fi
fi
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
if grep -q ' /mnt/usb ' /proc/mounts && [ -d /mnt/usb/download ]; then
  echo "usb: MOUNTED"
  awk '$2=="/mnt/usb"{print}' /proc/mounts | tail -1
else
  echo "usb: NOT_MOUNTED"
fi
echo "=== dns ==="
/etc/init.d/dnsmasq status 2>&1 | head -1 || /etc/init.d/dnsmasq-full status 2>&1 | head -1
echo "=== telegram ==="
tg=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 12 https://web.telegram.org/ 2>/dev/null || echo 000)
tip=$(nslookup telegram.org 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$tip" in
  198.18.*) fake=OK ;;
  *) fake=FAIL ;;
esac
case "$tg" in
  200|301|302) echo "telegram: OK http=$tg fakeip=$tip" ;;
  *) echo "telegram: FAIL http=$tg fakeip=$tip fake=$fake" ;;
esac
echo "=== torrents ==="
tip=$(nslookup rutracker.org 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$tip" in
  198.18.*) echo "torrents: OK fakeip=$tip" ;;
  *) echo "torrents: FAIL ip=${tip:-none}" ;;
esac
echo "=== youtube ==="
yt_ok=0
for i in 1 2 3; do
  r=$(curl -sI -m 10 https://www.youtube.com/generate_204 2>/dev/null | head -1)
  case "$r" in
    *" 204"*|*" 200"*) echo "$r"; yt_ok=1; break ;;
  esac
  [ "$i" -lt 3 ] && sleep 2
done
[ "$yt_ok" -eq 0 ] && echo "${r:-youtube: FAIL}"
yip=$(nslookup youtube.com 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$yip" in
  198.18.*) echo "youtube_dns: OK fakeip=$yip" ;;
  *) echo "youtube_dns: FAIL ip=${yip:-none}" ;;
esac
echo "=== ai ==="
aip=$(nslookup chatgpt.com 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$aip" in
  198.18.*) echo "ai: OK fakeip=$aip" ;;
  *) echo "ai: FAIL ip=${aip:-none}" ;;
esac
echo "=== urltest ==="
n=$(uci -q get podkop.main.urltest_proxy_links 2>/dev/null | wc -w)
echo "urltest: links=$n"
echo "=== selfheal ==="
if [ -x /usr/sbin/empire-singbox-lkg ] && /usr/sbin/empire-singbox-lkg smoke >/dev/null 2>&1; then
  echo "selfheal: OK"
else
  echo "selfheal: FAIL"
fi
echo "=== cron ==="
cl=$(wc -l </etc/crontabs/root 2>/dev/null || echo 0)
dup=$(grep -c empire-lan-watch /etc/crontabs/root 2>/dev/null || echo 0)
if [ "$dup" -le 1 ] && [ "$cl" -lt 40 ]; then
  echo "cron: OK lines=$cl lanwatch=$dup"
else
  echo "cron: FAIL lines=$cl lanwatch=$dup"
fi
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


def _ssh_ok(out: str) -> bool:
    """OpenWrt ash часто возвращает rc≠0 из-за последней команды в пайпе — смотрим маркеры."""
    return "=== hostname ===" in out and "=== selfheal ===" in out


def ssh_flint_via_reverse(remote_cmd: str) -> tuple[bool, str]:
    cmd = REV_SSH + [remote_cmd]
    _code, out = run_cmd(cmd, timeout=90)
    return _ssh_ok(out), out


def ssh_flint_via_ha(remote_cmd: str) -> tuple[bool, str]:
    inner = remote_cmd.replace("'", "'\"'\"'")
    hop = f"ssh -o BatchMode=yes -o ConnectTimeout=12 root@{FLINT} '{inner}'"
    _code, out = run_cmd(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HA_SSH, hop],
        timeout=120,
    )
    return _ssh_ok(out), out


def fetch_router_status() -> tuple[str | None, str]:
    """Returns (channel, raw_output). channel: reverse|ha|None"""
    for channel, fn in (("reverse", ssh_flint_via_reverse), ("ha", ssh_flint_via_ha)):
        ok, out = fn(REMOTE_CHECKS)
        if ok:
            return channel, out
        log(f"WARN: {channel} failed: {out[-200:]}")
    return None, ""


def parse_status(raw: str) -> dict:
    """ok: True/False подтверждено; None = unknown (не жжём бюджет, не валим all_ok)."""
    checks: dict[str, dict] = {}
    section = "general"

    def set_check(name: str, ok: bool | None, detail: str = "") -> None:
        checks[name] = {"ok": ok, "detail": (detail or "")[:200]}

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("=== ") and line.endswith(" ==="):
            section = line.strip("= ").lower().split()[0]
            continue
        low = line.lower()
        if section == "podkop":
            if "not_running" in low or "not running" in low or "inactive" in low or low.strip() == "stopped":
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
            elif line.startswith("nfqws:"):
                set_check("nfqws", "no" not in low, line)
            elif "nfqws" in low and "no" not in low:
                set_check("nfqws", True, line)
        elif section == "amnezia":
            if line.startswith("awg0:"):
                if "awg0: ok" in low:
                    set_check("awg0", True, line)
                else:
                    # NO / STALE / DEAD_PROBE
                    set_check("awg0", False, line)
            elif "never" in low and "handshake" in low:
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
                # важно: "not_mounted" содержит подстроку "mounted"
                if "not_mounted" in low or "not mounted" in low:
                    set_check("usb", False, line)
                elif "mounted" in low:
                    set_check("usb", True, line)
        elif section == "dns":
            if "not running" in low or "inactive" in low:
                set_check("dns", False, line)
            elif "running" in low or "started" in low:
                set_check("dns", True, line)
        elif section == "telegram":
            if line.startswith("telegram:"):
                set_check("telegram", "ok" in low, line)
        elif section == "torrents":
            if line.startswith("torrents:"):
                set_check("torrents", "ok" in low, line)
        elif section == "youtube":
            if line.startswith("HTTP/"):
                set_check("youtube", "204" in line or "200" in line, line)
            elif "youtube: fail" in low:
                set_check("youtube", False, line)
            elif line.startswith("youtube_dns:"):
                set_check("youtube_dns", "ok" in low, line)
        elif section == "ai":
            if line.startswith("ai:"):
                set_check("ai", "ok" in low, line)
        elif section == "urltest":
            if line.startswith("urltest:"):
                # links=3 → OK if >= 2
                n = 0
                if "links=" in low:
                    try:
                        n = int(low.split("links=")[1].split()[0])
                    except Exception:
                        n = 0
                set_check("urltest", n >= 2, line)
        elif section == "selfheal":
            if line.startswith("selfheal:"):
                set_check("selfheal", "ok" in low, line)
        elif section == "cron":
            if line.startswith("cron:"):
                set_check("cron", "ok" in low, line)

    if checks.get("sing-box", {}).get("ok") and checks.get("podkop", {}).get("ok") is not True:
        checks["podkop"] = {"ok": True, "detail": "sing-box process alive"}
    if checks.get("podkop", {}).get("ok") and checks.get("youtube", {}).get("ok"):
        checks.setdefault("sing-box", {"ok": True, "detail": "podkop+youtube ok"})
    # DNS FakeIP youtube — мягкий сигнал, не валит CRITICAL отдельно
    if checks.get("youtube_dns", {}).get("ok") is False and checks.get("youtube", {}).get("ok") is True:
        checks["youtube"] = {
            "ok": True,
            "detail": (checks["youtube"].get("detail") or "") + " (dns not fakeip)",
        }

    for key in (
        "podkop",
        "zapret",
        "nfqws",
        "transmission",
        "samba",
        "usb",
        "dns",
        "youtube",
        "awg0",
        "telegram",
        "torrents",
        "ai",
        "urltest",
        "selfheal",
        "cron",
    ):
        checks.setdefault(key, {"ok": None, "detail": "не проверено"})

    # all_ok только когда критичные явно зелёные
    all_ok = all(checks.get(k, {}).get("ok") is True for k in CRITICAL)
    confirmed_failed = [
        k for k in REMEDIABLE if checks.get(k, {}).get("ok") is False
    ]
    unknown = [k for k, v in checks.items() if v.get("ok") is None]
    return {
        "checks": checks,
        "all_ok": all_ok,
        "confirmed_failed": confirmed_failed,
        "unknown": unknown,
    }


def _ensure_rem(st: dict) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rem = st.setdefault("remediation", {})
    if rem.get("day") != today:
        # сохраняем last_fix_ts / fail_streak между днями не нужно — сброс суток
        rem.clear()
        rem["day"] = today
        rem["soft_n"] = 0
        rem["fixall_n"] = 0
        rem["last_fix_ts"] = {}
        rem["fail_streak"] = {}
    rem.setdefault("soft_n", 0)
    rem.setdefault("fixall_n", 0)
    rem.setdefault("last_fix_ts", {})
    rem.setdefault("fail_streak", {})
    return rem


def _on_success(st: dict, checks: dict) -> None:
    """После зелёных проверок сбрасываем серии неудач — день снова можно чинить."""
    rem = _ensure_rem(st)
    streak = rem.setdefault("fail_streak", {})
    for name, info in checks.items():
        if info.get("ok") is True and name in streak:
            streak.pop(name, None)


def remediate(channel: str, st: dict, failed: list[str], *, force: bool = False) -> list[str]:
    """Точечная починка с cooldown + эскалацией. force=True — ручной/экстренный прогон."""
    actions: list[str] = []
    rem = _ensure_rem(st)
    now = time.time()
    last_ts: dict = rem.setdefault("last_fix_ts", {})
    streak: dict = rem.setdefault("fail_streak", {})

    if force:
        for name in failed:
            last_ts.pop(name, None)
            streak.pop(name, None)
        last_ts.pop("fix_all", None)

    def ssh(cmd: str) -> tuple[int, str]:
        if channel == "reverse":
            return run_cmd(REV_SSH + [cmd], timeout=120)
        inner = cmd.replace("'", "'\"'\"'")
        hop = f"ssh -o BatchMode=yes root@{FLINT} '{inner}'"
        return run_cmd(["ssh", "-o", "BatchMode=yes", HA_SSH, hop], timeout=150)

    # Предпочитаем LKG/golden и flock — не голый podkop restart (race → duplicate ruleset)
    lkg = (
        "flock -n /var/lock/empire-heal.lock /usr/sbin/empire-singbox-lkg ensure 2>&1 | tail -5; "
        "echo lkg-ok"
    )
    fix_map = {
        "podkop": lkg,
        "youtube": lkg,
        "selfheal": lkg,
        "telegram": lkg,
        "ai": (
            "[ -x /usr/sbin/empire-awg-failover ] && /usr/sbin/empire-awg-failover ensure; "
            + lkg
        ),
        "urltest": lkg,
        "cron": (
            "[ -x /usr/sbin/empire-cron-normalize ] && /usr/sbin/empire-cron-normalize; "
            "echo cron-ok"
        ),
        "zapret": (
            "/etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null; "
            "echo zapret-ok"
        ),
        "nfqws": (
            "/etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null; "
            "echo nfqws-ok"
        ),
        "transmission": (
            "uci -q delete transmission.transmission; "
            "uci set transmission.@transmission[0].enabled=1; "
            "uci set transmission.@transmission[0].config_dir=/etc/transmission/config; "
            "uci set transmission.@transmission[0].config_overwrite=0; "
            "uci commit transmission; "
            "/etc/init.d/transmission enable 2>/dev/null; "
            "/etc/init.d/transmission restart 2>&1 | tail -3"
        ),
        "samba": "/etc/init.d/samba4 restart 2>&1 | tail -2",
        "awg0": (
            "[ -x /usr/sbin/empire-awg-failover ] && /usr/sbin/empire-awg-failover ensure; "
            "ifdown awg0 2>/dev/null; sleep 1; ifup awg0 2>/dev/null; "
            "sleep 3; echo awg-ok"
        ),
        "usb": (
            "/etc/init.d/empire-usb-mount start 2>/dev/null; "
            "/etc/init.d/samba4 restart 2>/dev/null; "
            "grep -q ' /mnt/usb ' /proc/mounts && [ -d /mnt/usb/download ] && echo usb-ok || echo usb-fail"
        ),
        "dns": (
            "/etc/init.d/dnsmasq restart 2>/dev/null || "
            "/etc/init.d/dnsmasq-full restart 2>/dev/null; echo dns-ok"
        ),
        "torrents": (
            "[ -x /usr/sbin/empire-flint-watchdog ] && "
            "flock -n /var/lock/empire-heal.lock /usr/sbin/empire-flint-watchdog --force "
            ">/tmp/empire-wd-force.out 2>&1; echo torrents-kick"
        ),
    }

    # youtube → тот же podkop: один cooldown-ключ, чтобы не долбить дважды
    to_fix: list[str] = []
    seen: set[str] = set()
    for name in failed:
        key = "podkop" if name in ("youtube", "podkop") else name
        if key in seen or key not in fix_map:
            continue
        seen.add(key)
        to_fix.append(key)

    did_soft = False
    for name in to_fix:
        prev = float(last_ts.get(name, 0) or 0)
        if not force and prev and (now - prev) < SOFT_COOLDOWN_SEC:
            left = int(SOFT_COOLDOWN_SEC - (now - prev))
            log(f"SKIP {name}: cooldown {left}s")
            actions.append(f"skip {name} (cooldown {left}s)")
            continue
        if not force and int(rem.get("soft_n", 0)) >= DAILY_SOFT_CAP:
            log(f"SKIP {name}: daily soft cap {DAILY_SOFT_CAP}")
            actions.append(f"skip {name} (daily soft cap)")
            continue

        log(f"REMEDIATE: {name}")
        code, out = ssh(fix_map[name])
        last_ts[name] = now
        rem["soft_n"] = int(rem.get("soft_n", 0)) + 1
        streak[name] = int(streak.get(name, 0)) + 1
        did_soft = True
        actions.append(f"fix {name} (rc={code})")
        log(f"  {out[-300:]}")

    # Эскалация: критичный подтверждённый сбой и soft уже не помогает / force
    crit_failed = [n for n in CRITICAL if n in failed]
    # youtube в failed → считаем podkop-стрик
    max_streak = 0
    for n in crit_failed:
        key = "podkop" if n in ("youtube", "podkop") else n
        max_streak = max(max_streak, int(streak.get(key, 0)))

    need_fixall = bool(crit_failed) and (
        force or (did_soft and max_streak >= ESCALATE_AFTER) or (not did_soft and max_streak >= ESCALATE_AFTER)
    )
    if need_fixall:
        prev_all = float(last_ts.get("fix_all", 0) or 0)
        if not force and prev_all and (now - prev_all) < FIXALL_COOLDOWN_SEC:
            left = int(FIXALL_COOLDOWN_SEC - (now - prev_all))
            log(f"SKIP fix-all: cooldown {left}s")
            actions.append(f"skip fix-all (cooldown {left}s)")
        elif not force and int(rem.get("fixall_n", 0)) >= DAILY_FIXALL_CAP:
            log(f"SKIP fix-all: daily cap {DAILY_FIXALL_CAP}")
            actions.append(f"skip fix-all (daily cap)")
        else:
            log("REMEDIATE: 13-fix-all.sh (эскалация)")
            fix_cmd = f"curl -fsSL {FIX_SCRIPT} 2>/dev/null | sh 2>&1 | tail -8"
            code, out = ssh(fix_cmd)
            last_ts["fix_all"] = now
            rem["fixall_n"] = int(rem.get("fixall_n", 0)) + 1
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
        ok = info.get("ok")
        if ok is True:
            icon = "✅"
        elif ok is False:
            icon = "❌"
        else:
            icon = "❔"
        icons.append(f"{icon} {name}")
    lines.append(" · ".join(icons[:8]))
    if len(icons) > 8:
        lines.append(" · ".join(icons[8:]))
    bad = [
        k
        for k, v in parsed.get("checks", {}).items()
        if v.get("ok") is False and k in (*CRITICAL, *REMEDIABLE)
    ]
    warn = [
        k
        for k, v in parsed.get("checks", {}).items()
        if v.get("ok") is False and k not in (*CRITICAL, *REMEDIABLE)
    ]
    unk = [k for k, v in parsed.get("checks", {}).items() if v.get("ok") is None]
    if bad:
        lines.append(f"⚠ проблемы: {', '.join(bad)}")
    if warn:
        lines.append(f"ℹ {', '.join(warn)}")
    if unk:
        lines.append(f"❔ не подтверждено: {', '.join(unk)}")
    if actions:
        lines.append("🔧 " + "; ".join(actions[:4]))
    return "\n".join(lines)


def main() -> int:
    check_only = "--check-only" in sys.argv
    no_fix = os.getenv("EMPIRE_ROUTER_NO_FIX", "") == "1" or "--no-fix" in sys.argv
    force_yt = (
        os.getenv("EMPIRE_ROUTER_FORCE_YOUTUBE_FIX", "") == "1"
        or "--force-youtube" in sys.argv
    )

    st = load_state()
    st["last_run"] = datetime.now(timezone.utc).isoformat()
    channel, raw = fetch_router_status()
    parsed = parse_status(raw) if raw else {
        "checks": {},
        "all_ok": False,
        "confirmed_failed": [],
        "unknown": [],
    }
    actions: list[str] = []

    if channel and force_yt and not no_fix and not check_only:
        log("FORCE YouTube fix: podkop + zapret")
        actions = remediate(channel, st, ["youtube", "podkop", "zapret", "nfqws"], force=True)
        time.sleep(5)
        channel, raw = fetch_router_status()
        parsed = parse_status(raw) if raw else parsed
    elif channel and not no_fix and not check_only:
        failed = list(parsed.get("confirmed_failed") or [])
        # unknown не чиним — только перепроверим в следующем тике / kick
        if failed:
            actions = remediate(channel, st, failed)
            time.sleep(8)
            channel2, raw2 = fetch_router_status()
            if channel2 and raw2:
                channel, parsed = channel2, parse_status(raw2)

    if channel:
        _on_success(st, parsed.get("checks") or {})

    # Если reverse SSH мёртв, а HA жив — поднять туннель с роутера
    if channel == "ha" and not no_fix and not check_only:
        rem = _ensure_rem(st)
        last_ts = rem.setdefault("last_fix_ts", {})
        prev = float(last_ts.get("fix_reverse", 0) or 0)
        now = time.time()
        if prev == 0 or (now - prev) >= SOFT_COOLDOWN_SEC:
            code, _ = run_cmd(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=8",
                    "-o",
                    "StrictHostKeyChecking=accept-new",
                    "-p",
                    "6223",
                    "root@127.0.0.1",
                    "echo ok",
                ],
                timeout=20,
            )
            if code != 0:
                log("REMEDIATE: flint2-tunnel/start.sh via HA")
                hop = (
                    "ssh -o BatchMode=yes -o ConnectTimeout=8 root@192.168.1.1 "
                    "'/etc/flint2-tunnel/start.sh 2>&1 | tail -3'"
                )
                rc, out = run_cmd(
                    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HA_SSH, hop],
                    timeout=60,
                )
                last_ts["fix_reverse"] = now
                rem["soft_n"] = int(rem.get("soft_n", 0)) + 1
                actions.append(f"restore reverse tunnel (rc={rc})")
                log(f"  {out[-200:]}")
                save_state(st)
                time.sleep(3)

    prev_ok = st.get("last_all_ok")
    summary = build_summary(channel, parsed, actions)
    st["last_channel"] = channel
    st["last_summary"] = summary
    st["last_all_ok"] = bool(parsed.get("all_ok"))
    st["last_checks"] = parsed.get("checks", {})
    st["last_actions"] = actions
    st["last_confirmed_failed"] = parsed.get("confirmed_failed") or []
    st["last_unknown"] = parsed.get("unknown") or []
    save_state(st)
    log(
        f"done channel={channel} all_ok={parsed.get('all_ok')} "
        f"failed={parsed.get('confirmed_failed')} actions={len(actions)}"
    )

    # Telegram: только если после починки всё ещё плохо (или роутер недоступен)
    _maybe_telegram_alert(channel, parsed, actions, summary, prev_ok=prev_ok)

    if os.getenv("EMPIRE_ROUTER_PRINT_SUMMARY") == "1":
        print(summary)
    return 0


def _maybe_telegram_alert(
    channel: str | None,
    parsed: dict,
    actions: list[str],
    summary: str,
    *,
    prev_ok: bool | None = None,
) -> None:
    if os.getenv("EMPIRE_ROUTER_NO_TELEGRAM", "").strip() in ("1", "true", "yes"):
        return
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import empire_notify as notify  # noqa: WPS433
    except Exception as exc:
        log(f"telegram import fail: {exc}")
        return

    cooldown = int(os.getenv("EMPIRE_ROUTER_TG_COOLDOWN", "1800"))
    failed = list(parsed.get("confirmed_failed") or [])
    crit_bad = [k for k in CRITICAL if k in failed]
    unreachable = channel is None
    all_ok = bool(parsed.get("all_ok")) and not unreachable
    still_bad = bool(crit_bad) or unreachable or not all_ok

    if not still_bad:
        # восстановление — только если раньше было плохо
        if prev_ok is False:
            notify.send(
                f"✅ Flint снова OK\n{summary}",
            )
            log("telegram recovery sent")
        return

    text = "🚨 Flint / VPN\n" + summary
    if actions:
        text += "\n🔧 уже пробовал: " + "; ".join(actions[:5])
    if len(text) > 3500:
        text = text[:3480] + "\n…"
    sent = notify.send_if_changed("flint_router_alert", text, min_interval_sec=cooldown)
    log(f"telegram alert sent={sent} crit={crit_bad}")

if __name__ == "__main__":
    raise SystemExit(main())
