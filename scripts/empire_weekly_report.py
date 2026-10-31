#!/usr/bin/env python3
"""Еженедельный сводный отчёт Empire → Telegram (воскресенье 08:00 МСК)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import empire_notify as notify  # noqa: E402

LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))


def send(text: str) -> bool:
    return notify.send(text)


def _parse_audit(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    m_status = re.search(r"status=(\w+) issues=(\d+) warnings=(\d+)", text)
    issues = []
    for line in text.splitlines():
        if "ISSUE:" in line:
            issues.append(line.split("ISSUE:", 1)[-1].strip())
        elif "WARN:" in line and len(issues) < 8:
            issues.append("⚠ " + line.split("WARN:", 1)[-1].strip())
    disk = re.search(r"OK: /: [^/]+/[^/]+ \((\d+)%\)", text)
    return {
        "date": path.name.replace("daily-audit-", "").replace(".log", "")[:8],
        "status": m_status.group(1) if m_status else "?",
        "issues_n": int(m_status.group(2)) if m_status else 0,
        "warnings_n": int(m_status.group(3)) if m_status else 0,
        "disk_pct": int(disk.group(1)) if disk else None,
        "top_issues": issues[:6],
    }


def _service_states() -> list[str]:
    names = [
        "empire_main",
        "empire_gdepar",
        "empire_worker",
        "empire_webapp",
        "empire_dashboard",
        "empire_stern_bot",
        "empire_ha_notify",
    ]
    out = []
    for u in names:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", u],
                capture_output=True,
                text=True,
                timeout=5,
            )
            st = (r.stdout or r.stderr or "?").strip()
            icon = "✅" if st == "active" else "⏸" if st == "inactive" else "❌"
            out.append(f"{icon} {u}: {st}")
        except Exception:
            out.append(f"❓ {u}")
    return out


def _posting_summary() -> list[str]:
    lines = []
    try:
        cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
        personas = [k for k in cfg if k not in ("defaults", "_comment")]
        lines.append(f"Каналы в расписании: {', '.join(sorted(personas))}")
    except Exception:
        pass
    used = ROOT / "data" / "stern_technique_used.json"
    matrix = ROOT / "data" / "stern_technique_matrix_161_200.json"
    if matrix.is_file():
        data = json.loads(matrix.read_text(encoding="utf-8"))
        ready = sum(1 for e in data.get("entries", []) if e.get("status") == "ready")
        used_n = 0
        if used.is_file():
            used_n = len(json.loads(used.read_text()).get("ids") or [])
        lines.append(f"Штерн видео-техника: опубликовано/взято {used_n}, в очереди ~{max(0, ready - used_n)}")
    try:
        r = httpx.get("http://127.0.0.1:8001/api/gdepar/health", timeout=8.0)
        if r.status_code == 200:
            h = r.json()
            lines.append(f"gdepar health: OK (assistant={h.get('assistant')})")
        else:
            lines.append(f"gdepar health: HTTP {r.status_code}")
    except Exception as exc:
        lines.append(f"gdepar health: недоступен ({exc})")
    return lines


def _night_pipelines(days: int = 7) -> list[str]:
    logs = sorted(LOG_DIR.glob("night-pipeline-*.log"), reverse=True)[:days]
    lines = []
    for p in logs[:3]:
        body = p.read_text(encoding="utf-8", errors="replace")
        ok = "DONE" in body
        lines.append(f"{'✅' if ok else '⚠'} {p.name}: {'завершён' if ok else 'не завершён/обрезан'}")
    return lines


def build_report() -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    audits = []
    for p in sorted(LOG_DIR.glob("daily-audit-*.log")):
        if p.is_symlink():
            continue
        try:
            day = datetime.strptime(p.name[12:20], "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day >= since:
            audits.append(_parse_audit(p))

    host = os.uname().nodename
    lines = [
        f"📊 Empire · еженедельный отчёт",
        f"Хост: {host} · период: последние 7 дней",
        "",
        "── Аудиты (ежедневно 07:00 МСK) ──",
    ]
    if not audits:
        lines.append("⚠ Нет daily-audit логов за неделю (проверьте empire-daily-audit.timer)")
    else:
        bad = sum(1 for a in audits if a["status"] != "OK")
        lines.append(f"Прогонов: {len(audits)}, с проблемами: {bad}")
        last = audits[-1]
        lines.append(
            f"Последний: {last['status']} · issues={last['issues_n']} warnings={last['warnings_n']}"
            + (f" · диск {last['disk_pct']}%" if last.get("disk_pct") else "")
        )
        for item in last.get("top_issues") or []:
            lines.append(f"  • {item[:120]}")

    lines.extend(["", "── Ночной бэкап (01:00 МСK) ──"])
    lines.extend(_night_pipelines() or ["(нет логов)"])

    lines.extend(["", "── Сервисы ──"])
    lines.extend(_service_states())

    lines.extend(["", "── Постинг / продукты ──"])
    lines.extend(_posting_summary())
    try:
        from empire_gdepar_parse_summary import build_gdepar_parse_summary

        lines.extend(["", build_gdepar_parse_summary()])
    except Exception as exc:
        lines.append(f"── Где Пар · парсинг ──\n⚠ {exc}")
    pm_path = LOG_DIR / "posting-metrics-latest.txt"
    kpi_path = ROOT / "data" / "empire_weekly_kpi.json"
    if pm_path.is_file():
        lines.extend(["", "── Эффективность постинга (неделя) ──"])
        lines.extend(pm_path.read_text(encoding="utf-8", errors="replace").splitlines()[:12])
    if kpi_path.is_file():
        try:
            hist = json.loads(kpi_path.read_text(encoding="utf-8"))
            last = hist[-1] if isinstance(hist, list) and hist else hist
            kpi = (last or {}).get("kpi") or {}
            lines.append(
                f"KPI: published={kpi.get('tg_posts_published')} "
                f"skip={kpi.get('autopost_failures')} "
                f"rate={kpi.get('autopost_success_rate')}"
            )
        except Exception:
            pass
    ca_path = LOG_DIR / "content-audit-latest.txt"
    if ca_path.is_file():
        ca_body = ca_path.read_text(encoding="utf-8", errors="replace")
        first = ca_body.splitlines()[:8]
        lines.extend(["", "── Аудит контента (вс 09:00) ──"])
        lines.extend(first)
        if "с замечаниями:" in ca_body:
            m = re.search(r"с замечаниями: (\d+)", ca_body)
            if m and int(m.group(1)) > 0:
                lines.append("  (полный отчёт: content-audit-latest.txt)")

    lines.extend(
        [
            "",
            "── Следующие проверки ──",
            "• Ежедневно 07:00 МСK — empire-daily-audit (Telegram)",
            "• Ежедневно 01:00 МСK — night-pipeline (бэкапы)",
            "• Каждые 10 мин — guard main.py",
            "• Каждые 2 ч — diagnostics-watchdog (автопочинка + Telegram)",
            "• Этот отчёт — вс 08:00 МСK",
            "",
            f"📄 Логи: {LOG_DIR}/daily-audit-latest.log",
        ]
    )
    text = "\n".join(lines)
    max_len = int(os.getenv("EMPIRE_AUDIT_TELEGRAM_MAX", "3900"))
    if len(text) > max_len:
        text = text[: max_len - 20] + "\n… (обрезано)"
    return text


def main() -> int:
    report_path = LOG_DIR / f"weekly-report-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"
    text = build_report()
    report_path.write_text(text, encoding="utf-8")
    (LOG_DIR / "weekly-report-latest.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0 if send(text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
