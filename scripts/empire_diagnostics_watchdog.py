#!/usr/bin/env python3
"""Watchdog самодиагностики Empire: таймеры, логи, автопочинка, Telegram.

Запуск: systemd empire-diagnostics-watchdog.timer (каждые 2 ч + после boot).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
STATE_PATH = Path(os.getenv("EMPIRE_DIAG_STATE", "/var/log/empire/diagnostics-state.json"))

TIMERS = (
    "empire-daily-audit.timer",
    "empire-night-pipeline.timer",
    "empire-weekly-report.timer",
    "empire-main-py-guard.timer",
    "empire-diagnostics-watchdog.timer",
    "empire-router-watchdog.timer",
    "empire-morning-brief.timer",
)

WATCHDOG_LOG = LOG_DIR / "diagnostics-watchdog.log"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with WATCHDOG_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


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


def run(cmd: list[str], timeout: int = 7200, env: dict | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out[-4000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, str(exc)


def timer_enabled(name: str) -> bool:
    code, out = run(["systemctl", "is-enabled", name], timeout=15)
    return code == 0 and "enabled" in out


def timer_last_trigger(name: str) -> datetime | None:
    code, out = run(
        ["systemctl", "show", name, "-p", "LastTriggerUSec", "--value"],
        timeout=15,
    )
    if code != 0 or not out.strip() or out.strip() in ("n/a", "0"):
        return None
    try:
        # microseconds since epoch
        us = int(out.strip())
        return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc)
    except Exception:
        return None


def read_latest_audit() -> dict:
    p = LOG_DIR / "daily-audit-latest.log"
    if not p.is_file():
        return {"ok": False, "reason": "нет daily-audit-latest.log"}
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"status=(\w+) issues=(\d+) warnings=(\d+)", text)
    if not m:
        return {"ok": False, "reason": "аудит не завершён (нет status=)", "mtime": p.stat().st_mtime}
    issues = [ln.split("ISSUE:", 1)[-1].strip() for ln in text.splitlines() if "ISSUE:" in ln]
    return {
        "ok": True,
        "status": m.group(1),
        "issues": int(m.group(2)),
        "warnings": int(m.group(3)),
        "mtime": p.stat().st_mtime,
        "top_issues": issues[:8],
        "path": str(p),
    }


def read_night_pipeline() -> dict:
    p = LOG_DIR / "night-pipeline-latest.log"
    if not p.is_file():
        return {"ok": False, "reason": "нет night-pipeline-latest.log"}
    text = p.read_text(encoding="utf-8", errors="replace")
    done = "night pipeline DONE" in text
    return {"ok": done, "mtime": p.stat().st_mtime, "reason": None if done else "не завершён", "path": str(p)}


def yandex_latest_day() -> str | None:
    host = os.uname().nodename.split(".")[0]
    remote = f"yandex:VPS-backup/{host}/"
    code, out = run(["rclone", "lsf", remote, "--dirs-only"], timeout=120)
    if code != 0:
        return None
    days = sorted(
        d.rstrip("/")
        for d in out.splitlines()
        if re.match(r"^\d{4}-\d{2}-\d{2}/?$", d.strip())
    )
    return days[-1] if days else None


def orphan_rclone_large() -> bool:
    code, out = run(["pgrep", "-af", "empire-large"], timeout=10)
    return code == 0 and bool(out.strip())


def pipeline_running() -> bool:
    code, out = run(["pgrep", "-af", "empire_night_pipeline.sh"], timeout=10)
    return code == 0 and bool(out.strip())


def tox1_uploading() -> bool:
    for pat in ("vps_large_files_to_cloud.sh tox1-yandex", "rclone copyto.*TOX1/parts/"):
        code, out = run(["pgrep", "-af", pat], timeout=10)
        if code == 0 and out.strip():
            return True
    return False


def stuck_yandex_rclone_h() -> float | None:
    code, out = run(["pgrep", "-af", "rclone copy.*/empire"], timeout=10)
    if code != 0 or not out.strip():
        return None
    pid = out.strip().split()[0]
    code2, et = run(["ps", "-o", "etimes=", "-p", pid], timeout=5)
    if code2 != 0:
        return None
    try:
        return int(et.strip()) / 3600
    except ValueError:
        return None


def tox1_cloud_parts() -> int:
    # rclone путь = short hostname (moderate-amethys), не FQDN
    host = os.uname().nodename.split(".")[0]
    remote = f"yandex:VPS-backup/{host}/TOX1/parts/"
    code, out = run(["rclone", "lsf", remote], timeout=90)
    if code != 0:
        return -1
    return sum(1 for ln in out.splitlines() if ".img.part" in ln)


def remediate_tox1_supervisor(st: dict) -> bool:
    if tox1_uploading():
        return False
    attempts = st.setdefault("remediation", {}).get("tox1_sup", 0)
    if attempts >= 3:
        return False
    log("REMEDIATE: empire_tox1_supervisor.sh")
    code, _ = run(["bash", str(ROOT / "scripts/empire_tox1_supervisor.sh")], timeout=60)
    st.setdefault("remediation", {})["tox1_sup"] = attempts + 1
    save_state(st)
    return code == 0


def remediate_unblock(st: dict) -> bool:
    if tox1_uploading():
        log("SKIP unblock: TOX1 выгрузка идёт")
        return False
    attempts = st.setdefault("remediation", {}).get("unblock", 0)
    if attempts >= 2:
        return False
    log("REMEDIATE: empire_unblock_backups.sh (зависший rclone/пайплайн)")
    env = os.environ.copy()
    env["EMPIRE_STALE_PIPELINE_H"] = "2"
    env["EMPIRE_UNBLOCK_FORCE"] = "0"
    code, _ = run(
        ["bash", str(ROOT / "scripts/empire_unblock_backups.sh")],
        timeout=120,
        env=env,
    )
    st.setdefault("remediation", {})["unblock"] = attempts + 1
    save_state(st)
    return code == 0


def remediate_audit(st: dict) -> bool:
    attempts = st.setdefault("remediation", {}).get("audit", 0)
    if attempts >= 2:
        log("SKIP remediate audit: лимит попыток за цикл watchdog")
        return False
    log("REMEDIATE: запуск empire_daily_audit.sh")
    code, out = run([str(ROOT / "scripts/empire_daily_audit.sh")], timeout=900)
    st.setdefault("remediation", {})["audit"] = attempts + 1
    save_state(st)
    log(f"audit remediate exit={code}")
    return code == 0


def remediate_yandex_backup(st: dict) -> bool:
    attempts = st.setdefault("remediation", {}).get("yandex", 0)
    if attempts >= 1:
        return False
    log("REMEDIATE: запуск vps_backup_to_yandex.sh (только код)")
    code, _ = run([str(ROOT / "scripts/vps_backup_to_yandex.sh")], timeout=7200)
    st.setdefault("remediation", {})["yandex"] = attempts + 1
    save_state(st)
    return code == 0


def read_router_state() -> dict:
    p = Path(os.getenv("EMPIRE_ROUTER_STATE", str(LOG_DIR / "router-state.json")))
    if not p.is_file():
        return {"ok": False, "reason": "router-state.json нет (empire-router-watchdog?)"}
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
        age_h = (time.time() - p.stat().st_mtime) / 3600
        return {
            "ok": bool(st.get("last_all_ok")),
            "summary": st.get("last_summary", "")[:400],
            "channel": st.get("last_channel"),
            "age_h": age_h,
            "actions": st.get("last_actions") or [],
        }
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def maybe_run_router_watchdog(st: dict) -> bool:
    """Запуск router watchdog если state старше 45 мин."""
    p = Path(os.getenv("EMPIRE_ROUTER_STATE", str(LOG_DIR / "router-state.json")))
    if p.is_file() and (time.time() - p.stat().st_mtime) < 45 * 60:
        return False
    attempts = st.setdefault("remediation", {}).get("router_wd", 0)
    if attempts >= 3:
        return False
    log("REMEDIATE: empire_router_watchdog.py")
    code, _ = run(
        [str(ROOT / "venv/bin/python"), str(ROOT / "scripts/empire_router_watchdog.py")],
        timeout=240,
    )
    st.setdefault("remediation", {})["router_wd"] = attempts + 1
    save_state(st)
    return code == 0


def build_report(
    *,
    timer_status: list[str],
    audit: dict,
    night: dict,
    yandex_day: str | None,
    tox1_parts: int,
    router: dict,
    actions: list[str],
    problems: list[str],
) -> str:
    host = os.uname().nodename
    lines = [
        f"🩺 Empire watchdog · {host}",
        f"Время UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "",
        "── Таймеры ──",
        *timer_status,
        "",
        "── Последний аудит ──",
    ]
    if audit.get("ok"):
        age_h = (time.time() - audit["mtime"]) / 3600
        lines.append(
            f"{audit['status']} · issues={audit['issues']} warnings={audit['warnings']} "
            f"({age_h:.1f}ч назад)"
        )
        for i in audit.get("top_issues") or []:
            lines.append(f"  • {i[:100]}")
    else:
        lines.append(f"❌ {audit.get('reason', '?')}")

    lines.append("")
    lines.append("── Ночной пайплайн ──")
    if night.get("ok"):
        age_h = (time.time() - night["mtime"]) / 3600
        lines.append(f"✅ завершён ({age_h:.1f}ч назад)")
    else:
        lines.append(f"⚠ {night.get('reason', '?')}")

    lines.append("")
    lines.append(f"── Я.Диск код-бэкап ──")
    lines.append(yandex_day or "❌ не удалось прочитать")

    lines.append("")
    lines.append("── TOX1 eMMC ──")
    if tox1_parts < 0:
        lines.append("❌ не читается")
    elif tox1_parts >= 10:
        lines.append(f"✅ {tox1_parts} частей на облаке")
    elif tox1_parts > 0:
        lines.append(f"⏳ {tox1_parts}/15 частей")
    elif tox1_uploading():
        lines.append("⏳ выгрузка идёт (part000+)")
    elif not Path("/root/tox1-backup/tox1-emmc-android-20260606.img").is_file():
        lines.append("✅ образ снят с VPS")
    else:
        lines.append("⚠ 30 ГБ образ ещё на VPS — ждёт выгрузки")

    lines.append("")
    lines.append("── Роутер Flint ──")
    if router.get("summary"):
        icon = "✅" if router.get("ok") else "⚠"
        lines.append(f"{icon} {router.get('channel', '?')} ({router.get('age_h', 0):.1f}ч назад)")
        for ln in (router.get("summary") or "").splitlines()[1:3]:
            if ln.strip():
                lines.append(f"  {ln[:100]}")
    else:
        lines.append(f"❌ {router.get('reason', 'не проверен')}")

    if actions:
        lines.extend(["", "── Автопочинка ──", *actions])
    if problems:
        lines.extend(["", "── Требует внимания ──", *[f"❌ {p}" for p in problems]])

    lines.append("")
    lines.append(f"📄 {LOG_DIR}/diagnostics-watchdog.log")
    return "\n".join(lines)


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    import empire_notify as notify  # noqa: E402

    st = load_state()
    st["last_watchdog"] = datetime.now(timezone.utc).isoformat()
    # сброс счётчиков remediation раз в сутки
    last_reset = st.get("remediation_reset_day")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if last_reset != today:
        st["remediation"] = {}
        st["remediation_reset_day"] = today
    save_state(st)

    problems: list[str] = []
    actions: list[str] = []
    timer_lines: list[str] = []

    for t in TIMERS:
        en = timer_enabled(t)
        last = timer_last_trigger(t)
        age = ""
        if last:
            age = f", последний {((datetime.now(timezone.utc) - last).total_seconds() / 3600):.1f}ч назад"
        icon = "✅" if en else "❌"
        timer_lines.append(f"{icon} {t}: {'enabled' if en else 'DISABLED'}{age}")
        if not en:
            problems.append(f"таймер {t} не enabled")
            run(["systemctl", "enable", "--now", t], timeout=30)
            actions.append(f"включён {t}")

    audit = read_latest_audit()
    audit_age_h = (time.time() - audit["mtime"]) / 3600 if audit.get("mtime") else 999
    if not audit.get("ok") or audit_age_h > 26:
        problems.append("ежедневный аудит устарел или не завершён")
        if remediate_audit(st):
            actions.append("перезапущен empire_daily_audit.sh")
            audit = read_latest_audit()

    night = read_night_pipeline()
    night_age_h = (time.time() - night["mtime"]) / 3600 if night.get("mtime") else 999
    if not night.get("ok") and night_age_h > 30:
        problems.append("ночной пайплайн не завершён >30ч")
    elif pipeline_running() and not night.get("ok"):
        if tox1_uploading():
            pass  # норма: пайплайн на TOX1
        else:
            stuck_h = stuck_yandex_rclone_h()
            if stuck_h is not None and stuck_h > 2:
                problems.append(f"yandex rclone завис ~{stuck_h:.1f}ч")
                if remediate_unblock(st):
                    actions.append("перезапуск пайплайна (unblock)")

    tox1_n = tox1_cloud_parts()
    if Path("/root/tox1-backup/tox1-emmc-android-20260606.img").is_file() and not tox1_uploading():
        if tox1_n == 0:
            problems.append("TOX1 образ 30 ГБ на VPS, выгрузка не идёт")
        sup = ROOT / "scripts/empire_tox1_supervisor.sh"
        if sup.is_file() and remediate_tox1_supervisor(st):
            actions.append("запущен empire_tox1_supervisor.sh")

    yday = yandex_latest_day()
    if yday:
        try:
            ydt = datetime.strptime(yday, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - ydt).days > 2:
                problems.append(f"Я.Диск код-бэкап устарел ({yday})")
                if not pipeline_running() and not orphan_rclone_large() and remediate_yandex_backup(st):
                    actions.append("запущен vps_backup_to_yandex.sh")
        except ValueError:
            pass
    else:
        if not pipeline_running():
            problems.append("не читается список бэкапов на Я.Диске")

    if orphan_rclone_large():
        problems.append("empire-large rclone всё ещё работает (может блокировать пайплайн)")

    if maybe_run_router_watchdog(st):
        actions.append("запущен empire_router_watchdog.py")
    router = read_router_state()
    if router.get("age_h", 999) > 1.5:
        problems.append("роутер не проверялся >1.5ч")
    elif not router.get("ok") and router.get("channel"):
        problems.append("роутер: podkop/VPN/torrent — проблемы")

    report = build_report(
        timer_status=timer_lines,
        audit=audit,
        night=night,
        yandex_day=yday,
        tox1_parts=tox1_n,
        router=router,
        actions=actions,
        problems=problems,
    )

    text_hash = str(hash(report))
    st["last_report_hash"] = text_hash
    st["pending_digest"] = report
    st["pending_digest_ts"] = time.time()
    save_state(st)

    sent = False
    if not os.getenv("EMPIRE_DIAG_NO_TELEGRAM"):
        sent = notify.send_twice_daily("watchdog", report)

    log(f"done problems={len(problems)} actions={len(actions)} telegram={sent}")
    if os.getenv("EMPIRE_DIAG_PRINT_REPORT"):
        print(report)
    # exit 0 для systemd даже при проблемах — они уже в логе и Telegram
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
