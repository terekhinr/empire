#!/usr/bin/env python3
"""Полный самохилер Empire: весь софт, сайты, роутер, HA, Docker.

Каждые ~5 мин проверяет и чинит (лимит рестартов), при сбое — Telegram.

ENV:
  EMPIRE_HEAL_DRY_RUN=1   — только отчёт
  EMPIRE_HEAL_NO_FIX=1    — без починки
  EMPIRE_HEAL_NO_TG=1     — без Telegram (по умолчанию хилер молчит в TG)
  EMPIRE_HEAL_FORCE_TG=1  — разовый полный отчёт в TG (иначе только утро/вечер digest)
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
STATE_PATH = Path(os.getenv("EMPIRE_HEAL_STATE", str(LOG_DIR / "service-healer-state.json")))
LOG_PATH = LOG_DIR / "service-healer.log"
ROUTER_STATE = Path(os.getenv("EMPIRE_ROUTER_STATE", str(LOG_DIR / "router-state.json")))

MAX_RESTARTS_PER_HOUR = int(os.getenv("EMPIRE_HEAL_MAX_RESTARTS", "2"))
DISK_WARN_PCT = float(os.getenv("EMPIRE_HEAL_DISK_WARN", "90"))
HA_SSH = os.getenv("EMPIRE_HA_SSH", "root@100.80.133.85")
HOME_OPS_API = (os.getenv("EMPIRE_HOME_OPS_API", "http://127.0.0.1:8767/api")).rstrip("/")
FLINT_TOKEN_FILE = Path(os.getenv("EMPIRE_FLINT_UI_TOKEN", "/etc/empire/flint-ui.token"))
FLINT_USB_FIX_KEY = os.getenv("EMPIRE_FLINT_USB_FIX_KEY", "flint_usb_fix")

CRITICAL_TIMERS = (
    "empire-service-healer.timer",
    "empire-router-watchdog.timer",
    "empire-diagnostics-watchdog.timer",
    "empire-daily-audit.timer",
    "empire-night-pipeline.timer",
    "empire-status-digest.timer",
    "empire-morning-brief.timer",
    "empire-main-py-guard.timer",
    "empire-vuln-remediate.timer",
)


@dataclass
class Check:
    name: str
    unit: str | None = None
    url: str | None = None
    optional: bool = False
    env_token: str | None = None
    docker: str | None = None  # имя контейнера
    require_json_ok: bool = True  # для health JSON: status=ok или ok=true
    public: bool = False  # публичный сайт: достаточно HTTP < 500


@dataclass
class Result:
    name: str
    ok: bool
    detail: str
    fixed: bool = False
    skipped: bool = False


@dataclass
class RunReport:
    results: list[Result] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(st: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def env_flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def run(cmd: list[str], timeout: int = 60, *, full: bool = False) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        if full:
            return p.returncode, out
        return p.returncode, out[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, str(exc)


def unit_active(unit: str) -> bool:
    code, out = run(["systemctl", "is-active", unit], timeout=10)
    return code == 0 and out.strip() == "active"


def unit_enabled(unit: str) -> bool:
    code, out = run(["systemctl", "is-enabled", unit], timeout=10)
    return code == 0 and "enabled" in out


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def env_token_set(name: str) -> bool:
    _load_dotenv()
    return bool((os.getenv(name) or "").strip())


def _ha_notify_url() -> str:
    _load_dotenv()
    port = (os.getenv("HA_NOTIFY_PORT") or "8766").strip() or "8766"
    return f"http://127.0.0.1:{port}/health"


def dns_resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def http_ok(url: str, *, require_json_ok: bool = True, timeout: float = 10.0) -> tuple[bool, str]:
    try:
        import httpx

        r = httpx.get(url, timeout=timeout, follow_redirects=True, verify=True)
        if r.status_code >= 500:
            return False, f"HTTP {r.status_code}"
        if r.status_code >= 400 and require_json_ok:
            # публичные health обычно 200; 404 на health = плохо
            return False, f"HTTP {r.status_code}"
        if not require_json_ok:
            return r.status_code < 400, f"HTTP {r.status_code}"
        ctype = (r.headers.get("content-type") or "").lower()
        if "json" in ctype:
            try:
                data = r.json()
                if isinstance(data, dict):
                    if "status" in data and data["status"] != "ok":
                        return False, f"status={data.get('status')}"
                    if "ok" in data and data["ok"] is False:
                        return False, "ok=false"
            except Exception:
                pass
        return True, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)[:140]


def build_checks() -> list[Check]:
    """Весь софт Empire на VPS + публичные сайты."""
    checks: list[Check] = [
        # Ядро приложений
        Check("gdepar", unit="empire_gdepar.service", url="http://127.0.0.1:8001/api/gdepar/health"),
        Check("webapp", unit="empire_webapp.service", url="http://127.0.0.1:8000/api/health"),
        Check("sales", unit="empire_sales.service", url="http://127.0.0.1:8002/health"),
        Check("planning", unit="empire_planning.service", url="http://127.0.0.1:8502/api/planning/health"),
        Check("dashboard", unit="empire_dashboard.service", url="http://127.0.0.1:8501/_stcore/health", require_json_ok=False),
        Check("main", unit="empire_main.service"),
        Check("worker", unit="empire_worker.service"),
        Check("ha_notify", unit="empire_ha_notify.service", url=_ha_notify_url()),
        Check("flint_bootstrap", unit="empire-flint2-bootstrap.service", url="http://127.0.0.1:8789/", require_json_ok=False),
        Check("nginx", unit="nginx.service"),
        Check("xray_8443", unit="xray-8443.service"),
        # Docker
        # Postgres-контейнер только если явно включён (EMPIRE_USE_DOCKER_DB=1).
        # На NEW/SQLite empire-db-1 нет — не рестартим и не шумим.
        Check(
            "docker_db",
            docker="empire-db-1",
            optional=os.getenv("EMPIRE_USE_DOCKER_DB", "").lower()
            not in ("1", "true", "yes"),
        ),
        Check("docker_amnezia", docker="amnezia-awg2"),
        # Опциональные боты
        Check("stern_bot", unit="empire_stern_bot.service", optional=True, env_token="STERN_BOT_TOKEN"),
        Check("garden_bot", unit="empire_garden_bot.service", optional=True, env_token="GARDEN_BOT_TOKEN"),
        Check("donate_bot", unit="empire_donate_bot.service", optional=True, env_token="DONATE_BOT_TOKEN"),
        # Публичные сайты (nginx → приложения)
        Check("site_gdepar", url="https://gdepar.ru/api/gdepar/health", public=True),
        Check("site_neverretire", url="https://neverretire.ru/api/health", public=True),
        Check("site_napensii", url="https://napensiyunikogda.ru/api/health", public=True, optional=True),
    ]
    return checks


def can_restart(st: dict[str, Any], key: str) -> bool:
    hist = st.setdefault("restarts", {}).setdefault(key, [])
    now = time.time()
    hist[:] = [t for t in hist if now - float(t) < 3600]
    return len(hist) < MAX_RESTARTS_PER_HOUR


def record_restart(st: dict[str, Any], key: str) -> None:
    hist = st.setdefault("restarts", {}).setdefault(key, [])
    hist.append(time.time())
    save_state(st)


def restart_unit(unit: str, *, dry: bool, no_fix: bool, st: dict[str, Any]) -> tuple[bool, str]:
    if dry or no_fix:
        return False, "skip fix (dry/no-fix)"
    if not can_restart(st, unit):
        return False, f"лимит рестартов ({MAX_RESTARTS_PER_HOUR}/ч)"
    log(f"RESTART {unit}")
    code, out = run(["systemctl", "restart", unit], timeout=120)
    record_restart(st, unit)
    time.sleep(2)
    ok = unit_active(unit)
    return ok, f"restart exit={code} active={ok}" + (f" {out[:60]}" if out and code else "")


def docker_running(name: str) -> bool:
    code, out = run(["docker", "inspect", "-f", "{{.State.Running}}", name], timeout=15)
    return code == 0 and out.strip().lower() == "true"


def handshake_age_seconds(line: str) -> int | None:
    """Parse WireGuard/Amnezia 'latest handshake: … ago' → seconds. Never → huge."""
    import re

    low = line.lower()
    if "never" in low:
        return 10**9
    if "handshake" not in low:
        return None
    total = 0
    found = False
    for n, unit in re.findall(r"(\d+)\s+(day|hour|minute|second)", low):
        found = True
        total += int(n) * {"day": 86400, "hour": 3600, "minute": 60, "second": 1}[unit]
    return total if found else None


def check_amnezia_flint_peer(*, dry: bool, no_fix: bool, st: dict[str, Any]) -> Result:
    """VPS-side: peer Flint на amnezia-awg2 — свежий handshake.

    Контейнер UP ≠ туннель жив. IP: EMPIRE_FLINT_AWG_IP (csv).
    Среди configured peers берём самый свежий handshake.

    EMPIRE_SKIP_AMNEZIA_PEER=1 — RKN/блок IP: не пинать peer до смены VPS.
    """
    if os.getenv("EMPIRE_SKIP_AMNEZIA_PEER", "").strip().lower() in ("1", "true", "yes", "on"):
        return Result(
            "amnezia_peer",
            True,
            "skip: EMPIRE_SKIP_AMNEZIA_PEER (ждём новый VPS)",
            skipped=True,
        )

    container = os.getenv("EMPIRE_AMNEZIA_CONTAINER", "amnezia-awg2")
    # .10 — актуальный Flint (docs); .13/.3 — legacy
    raw_ips = os.getenv("EMPIRE_FLINT_AWG_IP", "10.8.1.10,10.8.1.13,10.8.1.3")
    peer_ips = [x.strip() for x in raw_ips.split(",") if x.strip()]
    max_age = int(os.getenv("EMPIRE_AWG_MAX_AGE", "900"))

    if not docker_running(container):
        fixed = False
        detail = f"{container} not running"
        if not (dry or no_fix):
            ok, rdetail = restart_docker(container, dry=dry, no_fix=no_fix, st=st)
            fixed = ok
            detail = f"{detail} → {rdetail}"
        return Result("amnezia_peer", False, detail, fixed=fixed)

    code, out = run(["docker", "exec", container, "awg", "show"], timeout=30, full=True)
    if code != 0 or not out.strip():
        code, out = run(["docker", "exec", container, "wg", "show"], timeout=30, full=True)
    if code != 0 or not out.strip():
        return Result("amnezia_peer", False, f"{container}: awg/wg show fail")

    def _peer_meta(block: str) -> tuple[int | None, str | None, str]:
        age = None
        ip = None
        hs_line = ""
        for line in block.splitlines():
            low = line.lower()
            if "handshake" in low:
                age = handshake_age_seconds(line)
                hs_line = line.strip()
            if "allowed ips" in low:
                ip = line.split(":")[-1].strip().split("/")[0].strip()
        return age, ip, hs_line

    candidates: list[tuple[int, str, str]] = []  # age, ip, hs
    for block in out.split("peer:")[1:]:
        age, ip, hs_line = _peer_meta(block)
        if age is None or ip is None:
            continue
        if peer_ips and ip not in peer_ips:
            continue
        candidates.append((age, ip, hs_line))

    if not candidates:
        for block in out.split("peer:")[1:]:
            age, ip, hs_line = _peer_meta(block)
            if age is None:
                continue
            candidates.append((age, ip or "auto", hs_line))

    if not candidates:
        return Result(
            "amnezia_peer",
            False,
            f"peer {','.join(peer_ips) or '?'} не найден на {container}",
        )

    candidates.sort(key=lambda x: x[0])
    age, peer_ip, hs_line = candidates[0]
    if not hs_line:
        return Result("amnezia_peer", False, f"peer {peer_ip}: нет handshake")

    if age > max_age:
        detail = f"peer {peer_ip} STALE age={age}s ({hs_line})"
        if not (dry or no_fix):
            log("KICK empire_router_watchdog.py (amnezia peer stale)")
            py = ROOT / "venv/bin/python"
            rc, _ = run([str(py), str(ROOT / "scripts/empire_router_watchdog.py")], timeout=240)
            code2, out2 = run(["docker", "exec", container, "awg", "show"], timeout=30, full=True)
            age2 = None
            peer2 = peer_ip
            if code2 == 0 and out2.strip():
                c2: list[tuple[int, str]] = []
                for block in out2.split("peer:")[1:]:
                    a2, ip2, _ = _peer_meta(block)
                    if a2 is None or ip2 is None:
                        continue
                    if peer_ips and ip2 not in peer_ips:
                        continue
                    c2.append((a2, ip2))
                if c2:
                    c2.sort(key=lambda x: x[0])
                    age2, peer2 = c2[0]
            ok2 = age2 is not None and age2 <= max_age
            return Result(
                "amnezia_peer",
                ok2,
                f"{detail} → after kick(exit={rc}) peer {peer2} age={age2}",
                fixed=ok2,
            )
        return Result("amnezia_peer", False, detail)

    return Result("amnezia_peer", True, f"peer {peer_ip} ok age={age}s")



def restart_docker(name: str, *, dry: bool, no_fix: bool, st: dict[str, Any]) -> tuple[bool, str]:
    key = f"docker:{name}"
    if dry or no_fix:
        return False, "skip fix (dry/no-fix)"
    if not can_restart(st, key):
        return False, f"лимит рестартов ({MAX_RESTARTS_PER_HOUR}/ч)"
    log(f"DOCKER RESTART {name}")
    code, out = run(["docker", "restart", name], timeout=120)
    record_restart(st, key)
    time.sleep(3)
    ok = docker_running(name)
    return ok, f"docker restart exit={code} running={ok}" + (f" {out[:60]}" if out and code else "")


def check_one(c: Check, *, dry: bool, no_fix: bool, st: dict[str, Any]) -> Result:
    if c.env_token and not env_token_set(c.env_token):
        return Result(c.name, True, f"skip: нет {c.env_token}", skipped=True)
    if c.optional and c.unit and not unit_enabled(c.unit):
        return Result(c.name, True, "skip: unit не enabled", skipped=True)
    if c.public and c.url:
        host = urlparse(c.url).hostname or ""
        if host and not dns_resolves(host):
            if c.optional:
                return Result(c.name, True, f"skip: DNS {host}", skipped=True)
            return Result(c.name, False, f"DNS не резолвится: {host}")

    parts: list[str] = []

    if c.docker:
        running = docker_running(c.docker)
        parts.append(f"docker={'up' if running else 'DOWN'}")
        if not running:
            if c.optional:
                return Result(
                    c.name, True, "; ".join(parts) + " (optional skip)", skipped=True
                )
            fixed, detail = restart_docker(c.docker, dry=dry, no_fix=no_fix, st=st)
            parts.append(detail)
            if fixed:
                return Result(c.name, True, "; ".join(parts), fixed=True)
            return Result(c.name, False, "; ".join(parts))
        return Result(c.name, True, "; ".join(parts))

    if c.unit:
        active = unit_active(c.unit)
        parts.append(f"systemd={'active' if active else 'DOWN'}")
        if not active:
            fixed, detail = restart_unit(c.unit, dry=dry, no_fix=no_fix, st=st)
            parts.append(detail)
            if fixed:
                if c.url:
                    time.sleep(1)
                    ok, udetail = http_ok(c.url, require_json_ok=c.require_json_ok)
                    parts.append(udetail)
                    return Result(c.name, ok, "; ".join(parts), fixed=True)
                return Result(c.name, True, "; ".join(parts), fixed=True)
            if not (dry or no_fix):
                return Result(c.name, False, "; ".join(parts))

    if c.url:
        want_json = c.require_json_ok
        ok, detail = http_ok(c.url, require_json_ok=want_json)
        parts.append(detail)
        if not ok:
            if c.unit and not (dry or no_fix):
                fixed, rdetail = restart_unit(c.unit, dry=dry, no_fix=no_fix, st=st)
                parts.append(rdetail)
                if fixed:
                    ok2, detail2 = http_ok(c.url, require_json_ok=want_json)
                    parts.append(f"after:{detail2}")
                    if ok2:
                        return Result(c.name, True, "; ".join(parts), fixed=True)
            if c.optional:
                return Result(c.name, True, "; ".join(parts) + " (optional warn)", skipped=True)
            return Result(c.name, False, "; ".join(parts))

    return Result(c.name, True, "; ".join(parts) or "ok")


def telegram_bot_ok() -> tuple[bool, str]:
    _load_dotenv()
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    if not token:
        return False, "TELEGRAM_TOKEN пуст"
    try:
        import httpx

        r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15.0)
        if r.status_code != 200:
            return False, f"getMe HTTP {r.status_code}"
        data = r.json()
        if not data.get("ok"):
            return False, f"getMe not ok: {str(data.get('description', ''))[:80]}"
        uname = (data.get("result") or {}).get("username") or "?"
        return True, f"@{uname}"
    except Exception as exc:
        return False, str(exc)[:120]


def disk_usage_pct(path: str = "/") -> float:
    u = shutil.disk_usage(path)
    return 100.0 * (1.0 - u.free / u.total) if u.total else 0.0


def port_listening(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def _read_flint_token() -> str:
    try:
        if FLINT_TOKEN_FILE.is_file():
            return FLINT_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def check_flint_usb(*, dry: bool, no_fix: bool, no_tg: bool, st: dict[str, Any]) -> Result:
    """Проверка 'usb=true' из Flint empire-api; при падении — дергаем fix_all на всякий случай."""
    token = _read_flint_token()
    if not token:
        return Result("flint_usb", False, f"нет токена: {FLINT_TOKEN_FILE}")

    try:
        import httpx

        def api_get(action: str) -> tuple[bool, dict[str, Any] | None, str]:
            try:
                r = httpx.get(
                    f"{HOME_OPS_API}",
                    params={"action": action, "token": token},
                    timeout=20.0,
                    headers={"Authorization": f"Bearer {token}", "X-Empire-Token": token},
                )
                body = r.json() if r.content else {}
                if not isinstance(body, dict):
                    return False, None, f"bad json: {type(body)}"
                if body.get("ok") is True and action == "status":
                    return True, body, f"HTTP {r.status_code}"
                if body.get("ok") is True and action == "fix":
                    return True, body, f"HTTP {r.status_code}"
                return False, body, f"HTTP {r.status_code} ok={body.get('ok')}"
            except Exception as exc:
                return False, None, str(exc)[:140]

        ok, status_body, detail = api_get("status")
        if not ok or not status_body:
            return Result("flint_usb", False, f"status fail: {detail}")

        usb_ok = bool((status_body.get("checks") or {}).get("usb"))
        if usb_ok:
            return Result("flint_usb", True, "usb ok (Flint)")

        if dry or no_fix:
            return Result("flint_usb", False, "usb=false; skip fix (dry/no-fix)")
        if not can_restart(st, FLINT_USB_FIX_KEY):
            return Result("flint_usb", False, "usb=false; fix limitted (per hour)")

        # Автопочинка на Flint: запускаем empire-flint-watchdog --force (в т.ч. fix_usb)
        log("FLINT USB: try fix (action=fix)")
        _, _, fix_detail = api_get("fix")
        # mark restart в state (для ограничений)
        record_restart(st, FLINT_USB_FIX_KEY)
        time.sleep(5)
        ok2, status_body2, detail2 = api_get("status")
        usb_ok2 = bool((status_body2.get("checks") or {}).get("usb")) if ok2 and status_body2 else False
        if usb_ok2:
            return Result("flint_usb", True, f"usb fixed: {fix_detail}; after OK", fixed=True)
        return Result("flint_usb", False, f"usb still false after fix: {fix_detail}; after={detail2}")
    except Exception as exc:
        return Result("flint_usb", False, f"exception: {exc}"[:160])


def _home_ops_ha_ok() -> tuple[bool | None, str]:
    """True/False если empire-home-ops ответил; None если proxy недоступен."""
    token = _read_flint_token()
    if not token:
        return None, "no flint token"
    try:
        import httpx

        r = httpx.get(
            f"{HOME_OPS_API}",
            params={"action": "status", "token": token},
            timeout=15.0,
            headers={"Authorization": f"Bearer {token}", "X-Empire-Token": token},
        )
        body = r.json() if r.content else {}
        if not isinstance(body, dict) or body.get("ok") is not True:
            return None, f"home-ops HTTP {r.status_code}"
        ha = (body.get("checks") or {}).get("ha")
        if ha is True:
            return True, "home-ops checks.ha=true"
        if ha is False:
            return False, "home-ops checks.ha=false"
        return None, "home-ops: no ha field"
    except Exception as exc:
        return None, str(exc)[:100]


def check_ha_watcher(*, dry: bool, no_fix: bool) -> Result:
    """Глубокий HA-watcher (API + critical entities + Flint healer + HC ping)."""
    try:
        import empire_ha_watcher as haw
    except Exception as exc:
        return Result("homeassistant", False, f"watcher import: {exc}"[:120])
    try:
        report = haw.run_watch(dry=dry, no_fix=no_fix)
    except Exception as exc:
        return Result("homeassistant", False, f"watcher crash: {exc}"[:180])
    parts = [f"{r.name}={'ok' if r.ok else 'bad'}" for r in report.results if not r.skipped]
    detail = "; ".join(parts) if parts else "no checks"
    if report.problems:
        detail = f"{detail} · " + "; ".join(report.problems[:3])
    fixed = any(r.fixed for r in report.results)
    skipped = all(r.skipped for r in report.results) if report.results else False
    return Result("homeassistant", report.ok or skipped, detail[:220], fixed=fixed, skipped=skipped)


def check_ha(*, dry: bool, no_fix: bool, st: dict[str, Any]) -> Result:
    """Home Assistant API (Tailscale/tunnel); fallback — Flint home-ops checks.ha."""
    _load_dotenv()
    base = (os.getenv("HA_URL") or "http://127.0.0.1:18123").rstrip("/")
    token = (os.getenv("HA_TOKEN") or "").strip()
    if not token:
        return Result("homeassistant", True, "skip: нет HA_TOKEN", skipped=True)
    try:
        import httpx

        r = httpx.get(
            f"{base}/api/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        if r.status_code == 200:
            return Result("homeassistant", True, f"API {base} OK")
        detail = f"API HTTP {r.status_code}"
    except Exception as exc:
        detail = str(exc)[:140]

    # Fallback: Tailscale может быть logged out после миграции VPS —
    # Flint watchdog уже знает статус HA через LAN.
    hop_ok, hop_detail = _home_ops_ha_ok()
    if hop_ok is True:
        return Result(
            "homeassistant",
            True,
            f"{detail}; fallback OK ({hop_detail})",
            skipped=False,
        )
    if hop_ok is False:
        detail = f"{detail}; {hop_detail}"

    # починка
    if dry or no_fix:
        return Result("homeassistant", False, f"{detail}; skip fix")
    key = "ha:core"
    if not can_restart(st, key):
        return Result("homeassistant", False, f"{detail}; лимит restart HA")
    log(f"HA RESTART via SSH {HA_SSH}")
    code, out = run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=12",
            "-o",
            "StrictHostKeyChecking=accept-new",
            HA_SSH,
            "ha core restart || systemctl restart home-assistant@homeassistant || docker restart homeassistant || true",
        ],
        timeout=180,
    )
    record_restart(st, key)
    time.sleep(8)
    try:
        import httpx

        r2 = httpx.get(
            f"{base}/api/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
        if r2.status_code == 200:
            return Result(
                "homeassistant",
                True,
                f"{detail}; SSH restart exit={code} → OK",
                fixed=True,
            )
        # after restart still no API — trust home-ops if it recovers
        hop2, hop2d = _home_ops_ha_ok()
        if hop2 is True:
            return Result(
                "homeassistant",
                True,
                f"{detail}; after SSH home-ops OK ({hop2d})",
                fixed=True,
            )
        return Result("homeassistant", False, f"{detail}; after restart HTTP {r2.status_code}")
    except Exception as exc:
        hop2, hop2d = _home_ops_ha_ok()
        if hop2 is True:
            return Result(
                "homeassistant",
                True,
                f"{detail}; after={exc!s:.60}; home-ops OK ({hop2d})",
                fixed=True,
            )
        return Result("homeassistant", False, f"{detail}; after: {exc}"[:180])


def ensure_timers(*, dry: bool, no_fix: bool) -> list[str]:
    actions: list[str] = []
    for t in CRITICAL_TIMERS:
        if unit_enabled(t) and unit_active(t):
            continue
        msg = f"timer {t} enabled={unit_enabled(t)} active={unit_active(t)}"
        if dry or no_fix:
            actions.append(f"need enable {t} (dry)")
            continue
        log(f"ENABLE {t}")
        run(["systemctl", "enable", "--now", t], timeout=30)
        actions.append(f"enable --now {t}")
        if not unit_active(t):
            actions.append(f"FAIL still down: {msg}")
    return actions


def ensure_nginx_static_readable(*, dry: bool, no_fix: bool) -> list[str]:
    """Статика для nginx: зеркало /var/www/empire-static (не зависит от chmod /root)."""
    actions: list[str] = []
    src = ROOT / "static"
    dst = Path("/var/www/empire-static")
    if not src.is_dir():
        return actions
    # /root 755 — запасной путь, если alias ещё указывает в дерево проекта
    if os.path.isdir("/root"):
        root_mode = stat.S_IMODE(os.stat("/root").st_mode)
        if root_mode & 0o005 != 0o005:
            if dry or no_fix:
                actions.append(f"need chmod 755 /root (mode={oct(root_mode)})")
            else:
                os.chmod("/root", 0o755)
                actions.append("chmod 755 /root")
                log(actions[-1])
    need_sync = (not dst.is_dir()) or (
        (src / "site.css").is_file()
        and (
            not (dst / "site.css").is_file()
            or (src / "site.css").stat().st_mtime > (dst / "site.css").stat().st_mtime + 1
        )
    )
    if not need_sync and dst.is_dir():
        return actions
    if dry or no_fix:
        actions.append("need rsync static → /var/www/empire-static")
        return actions
    dst.parent.mkdir(parents=True, exist_ok=True)
    code, out = run(
        ["rsync", "-a", "--delete", f"{src}/", f"{dst}/"],
        timeout=120,
    )
    if code != 0:
        actions.append(f"FAIL rsync static: {out[:200]}")
        return actions
    run(["chown", "-R", "root:www-data", str(dst)], timeout=30)
    run(["chmod", "-R", "u=rwX,g=rX,o=rX", str(dst)], timeout=30)
    actions.append("rsync static → /var/www/empire-static")
    log(actions[-1])
    return actions


# Kick роутера: cooldown, не дневной потолок «4 и всё»
ROUTER_KICK_COOLDOWN_SEC = int(os.getenv("EMPIRE_HEAL_ROUTER_KICK_COOLDOWN", "900"))  # 15 мин
ROUTER_KICK_STALE_H = float(os.getenv("EMPIRE_HEAL_ROUTER_STALE_H", "0.6"))  # ~36 мин
ROUTER_KICK_DAILY_CAP = int(os.getenv("EMPIRE_HEAL_ROUTER_KICK_DAILY", "48"))  # страховка


def maybe_kick_router(st: dict[str, Any], *, dry: bool, no_fix: bool) -> tuple[Result, str | None]:
    """Статус Flint + автозапуск router-watchdog если плохо/устарело.

    Логика: cooldown 15 мин между kick; при all_ok сбрасываем серию;
    суточный cap высокий (страховка), не «утро сожгло день».
    """
    kick = st.setdefault("router_kick", {})
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if kick.get("day") != day:
        kick.clear()
        kick["day"] = day
        kick["n"] = 0
        kick["fail_streak"] = 0
        kick["last_ts"] = 0

    def _run_kick(reason: str) -> tuple[Result, str | None]:
        if dry or no_fix:
            return Result("router", False, f"{reason}; kick needed (dry)"), "router kick dry"
        now = time.time()
        last_ts = float(kick.get("last_ts", 0) or 0)
        if last_ts and (now - last_ts) < ROUTER_KICK_COOLDOWN_SEC:
            left = int(ROUTER_KICK_COOLDOWN_SEC - (now - last_ts))
            return Result("router", False, f"{reason}; cooldown {left}s"), None
        if int(kick.get("n", 0)) >= ROUTER_KICK_DAILY_CAP:
            return Result("router", False, f"{reason}; daily kick cap"), None

        log(f"KICK empire_router_watchdog.py ({reason})")
        py = ROOT / "venv/bin/python"
        code, _ = run([str(py), str(ROOT / "scripts/empire_router_watchdog.py")], timeout=240)
        kick["n"] = int(kick.get("n", 0)) + 1
        kick["last_ts"] = now
        kick["fail_streak"] = int(kick.get("fail_streak", 0)) + 1
        save_state(st)
        action = f"router watchdog exit={code}"
        try:
            data2 = json.loads(ROUTER_STATE.read_text(encoding="utf-8"))
            ok2 = bool(data2.get("last_all_ok"))
            if ok2:
                kick["fail_streak"] = 0
                save_state(st)
            summary = (data2.get("last_summary") or "")[:120]
            return Result("router", ok2, f"{summary or reason} → after kick ok={ok2}", fixed=ok2), action
        except Exception:
            return Result("router", False, reason), action

    if not ROUTER_STATE.is_file():
        return _run_kick("нет state")

    try:
        age_h = (time.time() - ROUTER_STATE.stat().st_mtime) / 3600
        data = json.loads(ROUTER_STATE.read_text(encoding="utf-8"))
        all_ok = bool(data.get("last_all_ok"))
        confirmed = list(data.get("last_confirmed_failed") or [])
        summary = (data.get("last_summary") or "").splitlines()
        short = summary[0] if summary else f"ok={all_ok}"
        if len(summary) > 1:
            short = f"{short} · {summary[1][:80]}"
        detail = f"{short} ({age_h:.1f}ч)"
    except Exception as exc:
        return Result("router", False, f"state битый: {exc}"), None

    if all_ok:
        kick["fail_streak"] = 0
        if age_h < ROUTER_KICK_STALE_H:
            save_state(st)
            return Result("router", True, detail), None
        # устарело — лёгкий re-probe
        return _run_kick(f"{detail}; stale")

    # не ok: kick если есть подтверждённый сбой или state свежий/старый всё равно
    reason = detail
    if confirmed:
        reason = f"{detail}; bad={','.join(confirmed[:4])}"
    return _run_kick(reason)


def build_summary(report: RunReport) -> str:
    host = os.uname().nodename
    lines = [
        f"🛠 Empire полный healer · {host}",
        f"UTC {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for r in report.results:
        if r.skipped:
            continue
        icon = "✅" if r.ok else "❌"
        fix = " → починил" if r.fixed else ""
        lines.append(f"{icon} {r.name}: {r.detail}{fix}")
    for e in report.extras:
        lines.append(e)
    if report.actions:
        lines.extend(["", "── Автопочинка ──", *[f"• {a}" for a in report.actions]])
    if report.problems:
        lines.extend(["", "── Проблемы ──", *[f"❌ {p}" for p in report.problems]])
    lines.append("")
    lines.append(f"📄 {LOG_PATH}")
    text = "\n".join(lines)
    # Telegram лимит ~4096
    if len(text) > 3900:
        text = text[:3850] + "\n…(обрезано)"
    return text


def fingerprint(report: RunReport) -> str:
    bits = []
    for r in report.results:
        if r.skipped:
            continue
        bits.append(f"{r.name}:{'1' if r.ok else '0'}:{'f' if r.fixed else '-'}")
    bits.extend(f"x:{x}" for x in report.problems)
    return "|".join(bits)


def notify(report: RunReport, *, dry: bool, no_tg: bool, force: bool) -> None:
    """Хилер чинит молча. В TG — только EMPIRE_HEAL_FORCE_TG=1.
    Сводка пишется в state → утро/вечер empire-status-digest."""
    text = build_summary(report)
    st = load_state()
    st["last_fp"] = fingerprint(report)
    st["last_summary"] = text[:2500]
    st["last_problems"] = list(report.problems)[:20]
    st["last_actions"] = list(report.actions)[:20]
    save_state(st)

    if dry or no_tg or not force:
        log("TG silent (digest morning/evening only)" if not force else "TG skipped")
        return
    try:
        import empire_notify as notify_mod
    except Exception as exc:
        log(f"notify import fail: {exc}")
        return
    notify_mod.send(text)


def main() -> int:
    dry = env_flag("EMPIRE_HEAL_DRY_RUN")
    no_fix = env_flag("EMPIRE_HEAL_NO_FIX")
    force_tg = env_flag("EMPIRE_HEAL_FORCE_TG")
    no_tg = not force_tg  # хилер молчит в TG; FORCE — разовый отчёт

    st = load_state()
    report = RunReport()
    log(f"START full dry={int(dry)} no_fix={int(no_fix)}")

    for c in build_checks():
        r = check_one(c, dry=dry, no_fix=no_fix, st=st)
        report.results.append(r)
        if r.fixed:
            report.actions.append(f"{r.name}: {r.detail}")
        if not r.ok and not r.skipped:
            report.problems.append(f"{r.name}: {r.detail}")
        log(f"  {r.name}: ok={r.ok} skip={r.skipped} fix={r.fixed} {r.detail}")

    # Home Assistant: deep watcher (API + critical entities + HC ping + Flint healer)
    ha = check_ha_watcher(dry=dry, no_fix=no_fix)
    report.results.append(ha)
    if ha.fixed:
        report.actions.append(f"ha: {ha.detail}")
    if not ha.ok and not ha.skipped:
        report.problems.append(f"ha: {ha.detail}")
    log(f"  ha: ok={ha.ok} fix={ha.fixed} {ha.detail}")

    # Роутер Flint
    router, router_action = maybe_kick_router(st, dry=dry, no_fix=no_fix)
    report.results.append(router)
    if router_action:
        report.actions.append(router_action)
    if router.fixed:
        report.actions.append(f"router: {router.detail}")
    if not router.ok and not router.skipped:
        report.problems.append(f"router: {router.detail}")
    log(f"  router: ok={router.ok} {router.detail}")

    # Amnezia server → peer Flint (handshake, не только docker up)
    am_peer = check_amnezia_flint_peer(dry=dry, no_fix=no_fix, st=st)
    report.results.append(am_peer)
    if am_peer.fixed:
        report.actions.append(f"amnezia_peer: {am_peer.detail}")
    if not am_peer.ok and not am_peer.skipped:
        report.problems.append(f"amnezia_peer: {am_peer.detail}")
    log(f"  amnezia_peer: ok={am_peer.ok} fixed={am_peer.fixed} {am_peer.detail}")

    # Reverse SSH туннель Flint → VPS
    rev_ok = port_listening(6223)
    report.results.append(
        Result("flint_reverse_ssh", rev_ok, "порт 6223 " + ("слушает" if rev_ok else "НЕТ (роутер не достучится)"))
    )
    if not rev_ok:
        report.problems.append("flint reverse SSH :6223 не слушает")

    # Доступность USB-диска роутера Flint (и автопочинка через PWA/WATCHDOG fix).
    flint_usb = check_flint_usb(dry=dry, no_fix=no_fix, no_tg=no_tg, st=st)
    report.results.append(flint_usb)
    if flint_usb.fixed:
        report.actions.append(f"flint_usb: {flint_usb.detail}")
    if not flint_usb.ok and not flint_usb.skipped:
        report.problems.append(f"flint_usb: {flint_usb.detail}")
    log(f"  flint_usb: ok={flint_usb.ok} fixed={flint_usb.fixed} {flint_usb.detail}")

    # Таймеры самопочинки
    for a in ensure_timers(dry=dry, no_fix=no_fix):
        report.actions.append(a)
        if a.startswith("FAIL"):
            report.problems.append(a)

    for a in ensure_nginx_static_readable(dry=dry, no_fix=no_fix):
        report.actions.append(a)
        if a.startswith("need "):
            report.problems.append(a)

    tg_ok, tg_detail = telegram_bot_ok()
    report.extras.append(f"{'✅' if tg_ok else '❌'} telegram getMe: {tg_detail}")
    if not tg_ok:
        report.problems.append(f"telegram: {tg_detail}")

    pct = disk_usage_pct("/")
    report.extras.append(f"{'✅' if pct < DISK_WARN_PCT else '❌'} disk /: {pct:.1f}%")
    if pct >= DISK_WARN_PCT:
        report.problems.append(f"disk {pct:.1f}%")

    summary = build_summary(report)
    st["last_run"] = datetime.now(timezone.utc).isoformat()
    st["last_ok"] = not report.problems
    st["last_summary"] = summary[:2500]
    st["last_fp"] = fingerprint(report)
    save_state(st)

    print(summary)
    notify(report, dry=dry, no_tg=no_tg, force=force_tg)
    log(f"DONE problems={len(report.problems)} actions={len(report.actions)}")
    # Не валим systemd oneshot: проблемы пишутся в state/digest.
    # Иначе timer+failed выглядят как авария, а ensure_timers не успевает жить.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
