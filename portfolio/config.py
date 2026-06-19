"""Конфигурация портфельного трекера."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PORTFOLIO_DB = Path(os.getenv("PORTFOLIO_DB", str(BASE_DIR / "portfolio.db")))
IMPORTS_DIR = Path(os.getenv("PORTFOLIO_IMPORTS_DIR", str(BASE_DIR / "data" / "portfolio_imports")))

TBANK_TOKEN = os.getenv("PORTFOLIO_TBANK_TOKEN", "").strip()
TBANK_ACCOUNT_ID = os.getenv("PORTFOLIO_TBANK_ACCOUNT_ID", "").strip()

DEFAULT_CUSHION_RUB = float(os.getenv("PORTFOLIO_CUSHION_RUB", "1500000"))

BROKERS = {
    "alfa": {
        "name": "Альфа-Инвестиции",
        "mode": "active",
        "currency": "RUB",
    },
    "tbank": {
        "name": "Т-Банк",
        "mode": "passive",
        "currency": "RUB",
    },
    "vtb": {
        "name": "ВТБ",
        "mode": "passive",
        "currency": "RUB",
    },
    "gpb": {
        "name": "Газпромбанк",
        "mode": "archive",
        "currency": "RUB",
    },
}

from portfolio.asset_classify import ASSET_CLASS_LABELS, ASSET_CLASS_ORDER
