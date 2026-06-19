"""sales.db — заказы, продукты, доступы (ТЗ §4.6–4.7)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

SALES_DB_PATH = Path(os.getenv("EMPIRE_SALES_DB", "sales.db"))
PRODUCTS_JSON = Path(__file__).resolve().parent / "data" / "stern_products.json"
GARDEN_PRODUCTS_JSON = Path(__file__).resolve().parent / "data" / "garden_products.json"
DONATE_JSON = Path(__file__).resolve().parent / "data" / "donate_products.json"
_PRODUCT_SEEDS = (PRODUCTS_JSON, GARDEN_PRODUCTS_JSON)
NPD_ANNUAL_LIMIT_RUB = float(os.getenv("EMPIRE_NPD_ANNUAL_LIMIT_RUB", "2400000"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_rub REAL NOT NULL,
    duration_days INTEGER DEFAULT 0,
    payments_enabled INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    product_code TEXT NOT NULL,
    amount_rub REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    tg_user_id INTEGER,
    yookassa_payment_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    receipt_url TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS course_users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    source_id TEXT,
    timezone TEXT DEFAULT 'Europe/Moscow',
    disclaimer_ok INTEGER DEFAULT 0,
    waitlist INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS entitlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    order_id INTEGER,
    expires_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    title TEXT,
    text_html TEXT,
    tg_file_id TEXT,
    fallback_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_source ON orders(source_id);
CREATE INDEX IF NOT EXISTS idx_entitlements_tg ON entitlements(tg_id);
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER NOT NULL,
    username TEXT,
    campaign_code TEXT NOT NULL,
    amount_stars INTEGER DEFAULT 0,
    amount_rub REAL DEFAULT 0,
    currency TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    telegram_payment_charge_id TEXT,
    invoice_payload TEXT,
    source_id TEXT,
    status TEXT DEFAULT 'paid',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_donations_campaign ON donations(campaign_code);
CREATE INDEX IF NOT EXISTS idx_donations_tg ON donations(tg_user_id);
"""


def init_sales_db(path: Path | None = None) -> None:
    p = path or SALES_DB_PATH
    conn = sqlite3.connect(p)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(_SCHEMA)
    _migrate_orders_tg_id(conn)
    conn.commit()
    seed_products(conn)
    conn.commit()
    conn.close()


def _migrate_orders_tg_id(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
    if "tg_user_id" not in cols:
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN tg_user_id INTEGER")
        except sqlite3.OperationalError:
            pass


def seed_products(conn: sqlite3.Connection) -> None:
    for path in _PRODUCT_SEEDS:
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        for p in raw.get("products", []):
            conn.execute(
                "INSERT OR REPLACE INTO products (code, name, price_rub, duration_days, payments_enabled) "
                "VALUES (?,?,?,?,?)",
                (
                    p["code"],
                    p["name"],
                    float(p["price_rub"]),
                    int(p.get("duration_days", 0)),
                    1 if p.get("payments_enabled") else 0,
                ),
            )


def list_products_for_persona(persona: str, *, only_payable: bool = False, path: Path | None = None) -> list[dict]:
    all_p = list_products(only_payable=only_payable, path=path)
    if persona == "garden":
        return [p for p in all_p if p["code"].startswith("garden_")]
    if persona == "stern":
        return [p for p in all_p if not p["code"].startswith("garden_")]
    return all_p


def list_products(*, only_payable: bool = False, path: Path | None = None) -> list[dict]:
    init_sales_db(path)
    p = path or SALES_DB_PATH
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    q = "SELECT code, name, price_rub, duration_days, payments_enabled FROM products"
    if only_payable:
        q += " WHERE payments_enabled = 1"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def annual_revenue_rub(path: Path | None = None) -> float:
    p = path or SALES_DB_PATH
    if not p.is_file():
        return 0.0
    conn = sqlite3.connect(p)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_rub), 0) FROM orders "
        "WHERE status IN ('paid', 'completed') "
        "AND created_at >= date('now', 'start of year')"
    ).fetchone()
    don = conn.execute(
        "SELECT COALESCE(SUM(amount_rub), 0) FROM donations "
        "WHERE status = 'paid' AND created_at >= date('now', 'start of year')"
    ).fetchone()
    conn.close()
    return float(row[0] or 0) + float(don[0] or 0)


def load_donate_campaigns(path: Path | None = None) -> dict[str, dict]:
    """Кампании донатов из data/donate_products.json."""
    if not DONATE_JSON.is_file():
        return {}
    raw = json.loads(DONATE_JSON.read_text(encoding="utf-8"))
    camps = raw.get("campaigns", {})
    return {k: v for k, v in camps.items() if isinstance(v, dict)}


def record_donation(
    *,
    tg_user_id: int,
    username: str | None,
    campaign_code: str,
    amount_stars: int = 0,
    amount_rub: float = 0,
    currency: str,
    payment_method: str,
    telegram_payment_charge_id: str | None = None,
    invoice_payload: str | None = None,
    source_id: str | None = None,
    path: Path | None = None,
) -> int:
    init_sales_db(path)
    p = path or SALES_DB_PATH
    conn = sqlite3.connect(p)
    cur = conn.execute(
        "INSERT INTO donations (tg_user_id, username, campaign_code, amount_stars, amount_rub, "
        "currency, payment_method, telegram_payment_charge_id, invoice_payload, source_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            tg_user_id,
            username,
            campaign_code,
            int(amount_stars),
            float(amount_rub),
            currency,
            payment_method,
            telegram_payment_charge_id,
            invoice_payload,
            source_id,
        ),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def donation_stats(*, campaign_code: str | None = None, days: int = 30, path: Path | None = None) -> dict:
    p = path or SALES_DB_PATH
    if not p.is_file():
        return {"count": 0, "stars_total": 0, "rub_total": 0.0}
    conn = sqlite3.connect(p)
    where = "status = 'paid' AND created_at >= datetime('now', ?)"
    params: list = [f"-{int(days)} days"]
    if campaign_code:
        where += " AND campaign_code = ?"
        params.append(campaign_code)
    row = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(amount_stars),0), COALESCE(SUM(amount_rub),0) FROM donations WHERE {where}",
        params,
    ).fetchone()
    conn.close()
    return {"count": int(row[0]), "stars_total": int(row[1]), "rub_total": float(row[2])}


def npd_limit_alert(path: Path | None = None) -> dict:
    rev = annual_revenue_rub(path)
    pct = (rev / NPD_ANNUAL_LIMIT_RUB * 100) if NPD_ANNUAL_LIMIT_RUB else 0
    return {
        "revenue_ytd_rub": rev,
        "limit_rub": NPD_ANNUAL_LIMIT_RUB,
        "pct": round(pct, 1),
        "alert": pct >= 80,
    }
