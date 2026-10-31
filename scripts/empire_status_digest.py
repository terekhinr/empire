#!/usr/bin/env python3
"""Утренний/вечерний отчёт о VPS в Telegram (не чаще 2×/сутки, 07/20 MSK)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import empire_notify as notify  # noqa: E402

STATE_PATH = Path(os.getenv("EMPIRE_DIAG_STATE", "/var/log/empire/diagnostics-state.json"))


def _fallback_report() -> str:
    if STATE_PATH.is_file():
        try:
            pending = json.loads(STATE_PATH.read_text(encoding="utf-8")).get("pending_digest")
            if pending:
                return str(pending)
        except Exception:
            pass
    return "⚠️ digest: watchdog не вернул отчёт — см. /var/log/empire/diagnostics-watchdog.log"


def _healer_block() -> str:
    heal_state = Path(os.getenv("EMPIRE_HEAL_STATE", "/var/log/empire/service-healer-state.json"))
    if not heal_state.is_file():
        return "── Хилер ──\n❓ нет state"
    try:
        st = json.loads(heal_state.read_text(encoding="utf-8"))
    except Exception:
        return "── Хилер ──\n❓ state битый"
    ok = st.get("last_ok")
    icon = "✅" if ok else "❌"
    run = (st.get("last_run") or "?")[:19]
    actions = st.get("last_actions") or []
    problems = st.get("last_problems") or []
    lines = [f"── Хилер · {run} UTC ──", f"{icon} last_ok={ok}"]
    if actions:
        lines.append("починил: " + "; ".join(str(a)[:80] for a in actions[:5]))
    if problems:
        lines.append("проблемы: " + "; ".join(str(p)[:80] for p in problems[:5]))
    return "\n".join(lines)


def _ha_home_block() -> str:
    """Offline critical HA entities + контракты комнат из empire_ha_watcher state."""
    path = Path(os.getenv("EMPIRE_HA_WATCH_STATE", "/var/log/empire/ha-watcher-state.json"))
    lines = ["── Дом / HA ──"]
    if not path.is_file():
        lines.append("❓ нет ha-watcher state")
        return "\n".join(lines)
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        lines.append("❓ state битый")
        return "\n".join(lines)
    offline = st.get("ha_offline") or []
    if not offline:
        lines.append("✅ critical entities online (или ещё не проверяли)")
    else:
        lines.append(f"❌ offline ({len(offline)}):")
        for row in offline[:8]:
            lines.append(f"· {row}")

    lines.append("── Дом / контракты ──")
    issues = st.get("room_contracts_issues") or []
    rows = st.get("room_contracts_digest") or []
    if issues:
        lines.append(f"❌ нарушений: {len(issues)}")
        for row in issues[:6]:
            lines.append(f"· {row}")
    elif rows:
        lines.append("✅ контракты OK")
        for row in rows[:4]:
            lines.append(f"· {row}")
    else:
        lines.append("❓ контракты ещё не считали (watcher)")
    return "\n".join(lines)


def _flint_vpn_block() -> str:
    """Сводка Flint/VPN из empire_router_watchdog state."""
    path = Path(os.getenv("EMPIRE_ROUTER_STATE", "/var/log/empire/router-state.json"))
    lines = ["── Flint / VPN ──"]
    if not path.is_file():
        lines.append("❓ нет router-state")
        return "\n".join(lines)
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        lines.append("❓ state битый")
        return "\n".join(lines)
    ok = st.get("last_all_ok")
    icon = "✅" if ok else "❌"
    run = (st.get("last_run") or "?")[:19]
    ch = st.get("last_channel") or "?"
    lines.append(f"{icon} all_ok={ok} · {ch} · {run} UTC")
    failed = st.get("last_confirmed_failed") or []
    if failed:
        lines.append("проблемы: " + ", ".join(str(x) for x in failed[:8]))
    summary = (st.get("last_summary") or "").strip()
    if summary:
        # короткая вторая строка иконок
        for ln in summary.splitlines()[1:3]:
            lines.append(ln[:200])
    return "\n".join(lines)


def main() -> int:
    slot = notify._digest_slot()
    if not slot:
        print("outside digest window, skip", flush=True)
        return 0

    # Перед отчётом — тихая ремедиация уязвимостей (без Telegram)
    rem = ROOT / "scripts/empire_vuln_remediate.sh"
    if rem.is_file():
        try:
            subprocess.run(
                ["bash", str(rem)],
                cwd=str(ROOT),
                timeout=900,
                env={**os.environ, "EMPIRE_APT_AUTOFIX": os.getenv("EMPIRE_APT_AUTOFIX", "1")},
                check=False,
            )
        except Exception as exc:
            print(f"vuln remediate warn: {exc}", flush=True)

    env = {**os.environ, "EMPIRE_DIAG_NO_TELEGRAM": "1", "EMPIRE_DIAG_PRINT_REPORT": "1"}
    py = ROOT / "venv/bin/python"
    report = ""
    try:
        r = subprocess.run(
            [str(py), str(ROOT / "scripts/empire_diagnostics_watchdog.py")],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
            cwd=str(ROOT),
        )
        report = (r.stdout or "").strip()
    except Exception as exc:
        report = f"⚠️ watchdog error: {exc}\n\n{_fallback_report()}"

    if not report:
        report = _fallback_report()

    # Отчёт по баням — только в empire-weekly-report (раз в неделю).
    healer = _healer_block()
    home = _ha_home_block()
    flint = _flint_vpn_block()
    label = "🌅 Утро" if "morning" in slot else "🌆 Вечер"
    text = f"{label} · Empire\n\n{report}\n\n{healer}\n\n{home}\n\n{flint}"
    if len(text) > 4000:
        text = text[:3980] + "\n… (обрезано)"

    ok = notify.send_twice_daily("status_digest", text)
    print(f"digest slot={slot} telegram={ok}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
