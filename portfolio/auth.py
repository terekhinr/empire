"""Пароль кабинета без Streamlit (общий для HTML и дашборда)."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

COOKIE_NAME = "empire_pf"
COOKIE_PATH = "/"
_COOKIE_SALT = b"empire-portfolio-v1"


def expected_password() -> str:
    env = os.getenv("EMPIRE_DASHBOARD_PASSWORD", "").strip()
    if env:
        return env
    path = Path("/etc/empire/dashboard_login.txt")
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "ПАРОЛЬ" in line.upper() and ":" in line:
                return line.split(":", 1)[1].strip()
    return ""


def password_matches(entered: str, expected: str) -> bool:
    left = hashlib.sha256(entered.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def session_token(password: str | None = None) -> str:
    pw = password if password is not None else expected_password()
    return hmac.new(_COOKIE_SALT, pw.encode("utf-8"), hashlib.sha256).hexdigest()


def cookie_ok(value: str | None) -> bool:
    pw = expected_password()
    if not pw or not value:
        return False
    return hmac.compare_digest(value, session_token(pw))
