#!/usr/bin/env python3
"""Короткий утренний отчёт 07:05 MSK: VPS + роутер + постинг — что работает."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import empire_notify as notify  # noqa: E402

LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
STATE_DIAG = Path(os.getenv("EMPIRE_DIAG_STATE", str(LOG_DIR / "diagnostics-state.json")))
STATE_ROUTER = Path(os.getenv("EMPIRE_ROUTER_STATE", str(LOG_DIR / "router-state.json")))


def _service_ok(unit: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (r.stdout or "").strip() == "active"
    except Exception:
        return False


def _audit_line() -> str:
    p = LOG_DIR / "daily-audit-latest.log"
    if not p.is_file():
        return "❌ аудит: нет лога"
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"status=(\w+) issues=(\d+) warnings=(\d+)", text)
    if not m:
        return "⚠ аудит: не завершён"
    st, iss, warn = m.group(1), m.group(2), m.group(3)
    icon = "✅" if st == "OK" else "⚠" if st == "WARN" else "❌"
    return f"{icon} аудит: {st} (i={iss} w={warn})"


def _router_line() -> str:
    if not STATE_ROUTER.is_file():
        return "❓ роутер: не проверялся"
    try:
        st = json.loads(STATE_ROUTER.read_text(encoding="utf-8"))
    except Exception:
        return "❓ роутер: state битый"
    if not st.get("last_channel"):
        return "❌ роутер: недоступен"
    if st.get("last_all_ok"):
        return f"✅ роутер ({st.get('last_channel')}): podkop/torrent OK"
    bad = [k for k, v in (st.get("last_checks") or {}).items() if not v.get("ok")]
    return f"⚠ роутер: {', '.join(bad[:5]) or 'проблемы'}"


def _posting_line() -> str:
    try:
        since = "24 hours ago"
        r = subprocess.run(
            ["journalctl", "-u", "empire_main", "--since", since, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        text = r.stdout or ""
        pub = text.count("[autopublish] published")
        skip = text.count("[autopublish] skip")
        icon = "✅" if skip == 0 else "⚠"
        return f"{icon} автопост 24ч: +{pub} skip={skip}"
    except Exception:
        return "❓ автопост: journalctl недоступен"


def _sites_line() -> str:
    parts = []
    for name, url in (("gdepar", "http://127.0.0.1:8001/api/gdepar/health"), ("web", "http://127.0.0.1:8000/")):
        try:
            import httpx

            r = httpx.get(url, timeout=6.0)
            parts.append(f"{'✅' if r.status_code < 500 else '❌'} {name}")
        except Exception:
            parts.append(f"❌ {name}")
    return " · ".join(parts)


def _backup_lines() -> list[str]:
    """HA + sqlite + Я.Диск — кратко для утреннего brief."""
    lines: list[str] = []
    audit = LOG_DIR / "daily-audit-latest.log"
    ha = "❓ HA: нет аудита"
    if audit.is_file():
        try:
            for ln in audit.read_text(encoding="utf-8", errors="replace").splitlines():
                if "HA бэкапов:" in ln or "HA недоступен" in ln:
                    clean = ln.split("] ", 1)[-1] if "] " in ln else ln
                    if clean.startswith("OK:"):
                        ha = f"✅ {clean[3:].strip()}"
                    elif clean.startswith("ISSUE:"):
                        ha = f"❌ {clean[6:].strip()}"
                    else:
                        ha = clean.strip()
                    break
        except Exception:
            pass
    lines.append(ha)

    d = Path("/var/backups/empire")
    dbs = sorted(d.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True) if d.is_dir() else []
    if dbs:
        age_h = (datetime.now(timezone.utc).timestamp() - dbs[0].stat().st_mtime) / 3600
        icon = "✅" if age_h < 36 else "⚠"
        lines.append(f"{icon} sqlite VPS: {age_h:.0f}ч назад")
    else:
        lines.append("❌ sqlite VPS: нет бэкапов")

    # Я.Диск день из diagnostics state / rclone через короткий вызов
    try:
        r = subprocess.run(
            ["rclone", "lsf", "yandex:VPS-backup/moderate-amethys/", "--dirs-only"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        days = sorted(
            ln.strip().rstrip("/")
            for ln in (r.stdout or "").splitlines()
            if re.match(r"^\d{4}-\d{2}-\d{2}/?$", ln.strip())
        )
        if days:
            lines.append(f"✅ Я.Диск настройки: {days[-1]}")
        else:
            lines.append("❌ Я.Диск: нет дневных папок")
    except Exception:
        lines.append("❓ Я.Диск: не проверен")
    return lines


def build_brief() -> str:
    now_msk = datetime.now(timezone.utc).astimezone(
        timezone.utc  # placeholder; label UTC for clarity
    )
    services = [
        ("main", "empire_main"),
        ("gdepar", "empire_gdepar"),
        ("worker", "empire_worker"),
    ]
    svc = " · ".join(
        f"{'✅' if _service_ok(u) else '❌'} {n}" for n, u in services
    )
    lines = [
        f"🌅 Утро · Empire · {now_msk.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        svc,
        _sites_line(),
        _audit_line(),
        _router_line(),
        _posting_line(),
    ]
    # disk quick
    try:
        r = subprocess.run(["df", "-hP", "/"], capture_output=True, text=True, timeout=5)
        row = (r.stdout or "").strip().splitlines()[-1]
        pct = row.split()[4] if len(row.split()) >= 5 else "?"
        lines.append(f"💾 диск /: {pct}")
    except Exception:
        pass
    lines.append("")
    lines.append("── Бэкапы ──")
    lines.extend(_backup_lines())
    # Парсинг бань — в weekly-отчёте, не в daily brief (проект сырой).
    lines.append("")
    lines.append("Полный лог: /var/log/empire/daily-audit-latest.log")
    return "\n".join(lines)


def main() -> int:
    # Запустить router watchdog перед отчётом (без блокировки утра)
    py = ROOT / "venv/bin/python"
    rw = ROOT / "scripts/empire_router_watchdog.py"
    if rw.is_file():
        env = {**os.environ, "EMPIRE_ROUTER_NO_FIX": os.getenv("EMPIRE_MORNING_NO_FIX", "0")}
        try:
            subprocess.run([str(py), str(rw)], timeout=180, env=env, cwd=str(ROOT))
        except Exception:
            pass

    text = build_brief()
    # TG только через empire-status-digest (утро+вечер). Brief — локальный лог + Я.Диск.
    skipped = os.getenv("EMPIRE_MORNING_FORCE") != "1"
    if not skipped:
        ok = notify.send(text)
    else:
        ok = False
        print("telegram=skipped (use empire-status-digest 07/20 MSK)", flush=True)
    print(text)
    print(f"telegram={ok}", flush=True)

    # Раз в сутки — аудит на Я.Диск (без ручного копирования)
    sync_sh = ROOT / "scripts" / "export_audit_to_yandex.sh"
    state_path = Path(os.getenv("EMPIRE_DIAG_STATE", "/var/log/empire/diagnostics-state.json"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        st = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    except Exception:
        st = {}
    if sync_sh.is_file() and st.get("yandex_audit_day") != today:
        try:
            subprocess.run(["bash", str(sync_sh)], cwd=str(ROOT), timeout=600, check=False)
            st["yandex_audit_day"] = today
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"yandex_audit synced ({today})", flush=True)
        except Exception as exc:
            print(f"yandex_audit warn: {exc}", flush=True)

    return 0 if (ok or skipped) else 1


if __name__ == "__main__":
    raise SystemExit(main())
