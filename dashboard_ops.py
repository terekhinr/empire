"""Ops helpers for Streamlit dashboard (systemd, HTTP health)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import requests

SYSTEMCTL = Path("/usr/bin/systemctl")
if not SYSTEMCTL.is_file():
    SYSTEMCTL = Path("/bin/systemctl")

# Отдельные Telegram-боты (не empire_main): лиды, оплата, донаты.
OPTIONAL_BOTS: dict[str, dict[str, str]] = {
    "empire_stern_bot": {
        "env": "STERN_BOT_TOKEN",
        "label": "Штерн · курс «Железная спина»",
        "note": "Лид-магнит и лист ожидания курса. Постинг канала — empire_main.",
    },
    "empire_garden_bot": {
        "env": "GARDEN_BOT_TOKEN",
        "label": "Сад · продажи PDF",
        "note": "Каталог и waitlist. Постинг канала — empire_main.",
    },
    "empire_donate_bot": {
        "env": "DONATE_BOT_TOKEN",
        "label": "Ленин · донаты Stars",
        "note": "Только донаты в канал «Ленин». Постинг — empire_main.",
    },
}

HTTP_CHECKS: dict[str, str] = {
    "empire_webapp": "http://127.0.0.1:8000/api/health",
    "empire_gdepar": "http://127.0.0.1:8001/api/gdepar/health",
    "empire_sales": "http://127.0.0.1:8002/health",
    "empire_dashboard": "http://127.0.0.1:8501/_stcore/health",
}


def _env_token(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def systemctl_status(unit: str) -> str:
    """Статус systemd-юнита. Полный путь к systemctl — PATH у dashboard только venv."""
    if not SYSTEMCTL.is_file():
        return "systemctl недоступен"
    try:
        r = subprocess.run(
            [str(SYSTEMCTL), "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (r.stdout or r.stderr or "").strip()
        return out or "unknown"
    except Exception as exc:
        return f"ошибка ({exc})"


def http_health_ok(key: str, timeout: float = 2.0) -> bool | None:
    url = HTTP_CHECKS.get(key)
    if not url:
        return None
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def service_row(unit_base: str) -> dict[str, str]:
    """Одна строка мониторинга: systemd + опционально HTTP + причина для ботов."""
    unit = f"{unit_base}.service"
    systemd = systemctl_status(unit)
    http_ok = http_health_ok(unit_base)

    if unit_base in OPTIONAL_BOTS:
        meta = OPTIONAL_BOTS[unit_base]
        env_name = meta["env"]
        if not _env_token(env_name):
            return {
                "unit": unit_base,
                "systemd": systemd,
                "http": "—",
                "display": "не настроен",
                "detail": f"Нет {env_name} в .env — бот не создавали в @BotFather или токен не прописан.",
            }
        if systemd != "active":
            return {
                "unit": unit_base,
                "systemd": systemd,
                "http": "—",
                "display": systemd,
                "detail": f"Токен есть. Запуск: systemctl start {unit}",
            }

    display = systemd
    if http_ok is True and systemd != "active":
        display = f"{systemd} · HTTP ok"
    elif http_ok is False:
        display = f"{systemd} · HTTP fail"

    return {
        "unit": unit_base,
        "systemd": systemd,
        "http": "ok" if http_ok else ("fail" if http_ok is False else "—"),
        "display": display,
        "detail": "",
    }
