"""Классификация активов: акции · ЗПИФ · золото · фонды ликвидности."""

from __future__ import annotations

import re

# Биржевые фонды денежного рынка (финансовая подушка)
LIQUIDITY_TICKERS = frozenset(
    {
        "LQDT",
        "SBMM",
        "TMON",
        "AKMM",
        "VTBM",
        "AMNY",
        "CNYM",
        "RUB000UTSTOM",
        "TMON@",
    }
)

GOLD_TICKERS = frozenset({"GLDRUB_TOM", "SLVRUB_TOM", "GOLD", "GOLDRUB"})

# Денежный остаток на счёте — не фонд ликвидности
CASH_TICKERS = frozenset({"RUB000UTSTOM", "USD000UTSTOM", "EUR000UTSTOM"})

ASSET_CLASS_ORDER = ("stock", "bond", "zpif", "gold", "liquidity")

ASSET_CLASS_LABELS = {
    "stock": "Акции",
    "bond": "Облигации",
    "zpif": "Паи ЗПИФ",
    "gold": "Золото",
    "liquidity": "Фонды ликвидности (подушка)",
}


def classify_asset(
    ticker: str,
    *,
    name: str | None = None,
    instrument_type: str | None = None,
) -> tuple[str, bool]:
    """
    Возвращает (asset_class, is_liquidity_fund).
    Четыре класса: stock | zpif | gold | liquidity.
    """
    t = (ticker or "").strip().upper().rstrip("@")
    n = (name or "").lower()

    if t in CASH_TICKERS:
        return "stock", False  # кэш не входит в 4 класса; позже можно скрыть

    # Золото считаем только как биржевой металл (GLDRUB_TOM и аналоги),
    # а не как акции золотодобытчиков (например UGLD).
    if t in GOLD_TICKERS or "gldrub_tom" in t.lower() or "slvrub_tom" in t.lower():
        return "gold", False

    if t in LIQUIDITY_TICKERS or t.rstrip("@") in LIQUIDITY_TICKERS:
        return "liquidity", True
    if any(k in n for k in ("lqdt", "sbmm", "tmon", "ликвид", "денежн", "фонд денеж")):
        return "liquidity", True

    itype = (instrument_type or "").lower()
    if "bond" in itype or any(k in n for k in ("облигац", "офз", "бонд", "coupon")):
        return "bond", False
    if t.startswith("SU") and "RMF" in t:
        return "bond", False

    if _is_zpif(t, n, instrument_type):
        return "zpif", False

    return "stock", False


def _is_zpif(ticker: str, name: str, instrument_type: str | None) -> bool:
    if instrument_type in ("etf",) and "зпиф" in name:
        return True
    if any(k in name for k in ("зпиф", "закрытый паев", "паевой", "пиф ", "пиф«", "пиф\"")):
        return True
    if re.search(r"парус", name):
        return True
    # внебиржевые ЗПИФ часто идут с ISIN без MOEX-тикера
    if ticker.startswith("RU000A") and any(k in name for k in ("зпиф", "пиф", "парус", "комбинирован")):
        return True
    if ticker.startswith("RU000A") and "etf" not in name and "акци" not in name and "облигац" not in name:
        if len(ticker) >= 12 and not name:
            return True
    return False


def normalize_legacy_class(asset_class: str) -> str:
    """Старые классы → новые четыре."""
    mapping = {
        "etf": "zpif",
        "other": "zpif",
    }
    if asset_class in ASSET_CLASS_LABELS:
        return asset_class
    return mapping.get(asset_class, "stock")
