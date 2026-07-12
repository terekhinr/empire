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


def main() -> int:
    slot = notify._digest_slot()
    if not slot:
        print("outside digest window, skip", flush=True)
        return 0

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

    label = "🌅 Утро" if "morning" in slot else "🌆 Вечер"
    text = f"{label} · Empire VPS\n\n{report}"
    if len(text) > 4000:
        text = text[:3980] + "\n… (обрезано)"

    ok = notify.send_twice_daily("status_digest", text)
    print(f"digest slot={slot} telegram={ok}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
