"""SQLite-схема portfolio.db."""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from portfolio.config import BROKERS, PORTFOLIO_DB

_init_lock = threading.Lock()
_initialized_paths: set[str] = set()


def _db_path_key(db_path: Path | None = None) -> str:
    return str((db_path or PORTFOLIO_DB).resolve())


def _retry_locked(fn, *, attempts: int = 10, base_delay: float = 0.05):
    last: sqlite3.OperationalError | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            last = exc
            time.sleep(base_delay * (attempt + 1))
    if last is not None:
        raise last
    raise RuntimeError("retry_locked failed without exception")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or PORTFOLIO_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = get_connection(db_path)
    try:
        yield conn
        _retry_locked(conn.commit)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _bootstrap_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS brokers (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'active',
            currency TEXT NOT NULL DEFAULT 'RUB'
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            broker_id INTEGER NOT NULL REFERENCES brokers(id),
            label TEXT NOT NULL,
            external_id TEXT,
            currency TEXT NOT NULL DEFAULT 'RUB',
            UNIQUE(broker_id, label)
        );

        CREATE TABLE IF NOT EXISTS instruments (
            id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            isin TEXT,
            name TEXT,
            asset_class TEXT NOT NULL DEFAULT 'stock',
            is_liquidity_fund INTEGER NOT NULL DEFAULT 0,
            UNIQUE(ticker)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            instrument_id INTEGER REFERENCES instruments(id),
            tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            quantity REAL,
            price REAL,
            amount REAL,
            fee REAL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'RUB',
            external_id TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(account_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS manual_positions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            instrument_id INTEGER NOT NULL REFERENCES instruments(id),
            quantity REAL NOT NULL,
            avg_price REAL,
            note TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(account_id, instrument_id)
        );

        CREATE TABLE IF NOT EXISTS cashflows (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            flow_date TEXT NOT NULL,
            amount REAL NOT NULL,
            flow_type TEXT NOT NULL,
            note TEXT,
            external_id TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(account_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS price_cache (
            ticker TEXT NOT NULL,
            price_date TEXT NOT NULL,
            price REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'moex',
            PRIMARY KEY (ticker, price_date)
        );

        CREATE TABLE IF NOT EXISTS monthly_snapshots (
            month TEXT PRIMARY KEY,
            total_value REAL NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_snapshots (
            snap_date TEXT PRIMARY KEY,
            total_value REAL NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    for code, meta in BROKERS.items():
        conn.execute(
            """
            INSERT INTO brokers (code, name, mode, currency)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                mode=excluded.mode,
                currency=excluded.currency
            """,
            (code, meta["name"], meta["mode"], meta["currency"]),
        )
        conn.execute(
            """
            INSERT INTO accounts (broker_id, label, currency)
            SELECT id, 'Основной', ?
            FROM brokers WHERE code = ?
            ON CONFLICT(broker_id, label) DO NOTHING
            """,
            (meta["currency"], code),
        )
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('cushion_rub', ?)
        ON CONFLICT(key) DO NOTHING
        """,
        (str(__import__("portfolio.config", fromlist=["DEFAULT_CUSHION_RUB"]).DEFAULT_CUSHION_RUB),),
    )
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('portfolio_ui_mode', 'snowball')
        ON CONFLICT(key) DO NOTHING
        """
    )


def init_db(conn: sqlite3.Connection | None = None, db_path: Path | None = None) -> None:
    own = conn is None
    if own:
        conn = get_connection(db_path)
    path_key = _db_path_key(db_path)

    if path_key in _initialized_paths:
        if own:
            conn.close()
        return

    with _init_lock:
        if path_key in _initialized_paths:
            if own:
                conn.close()
            return

        def _run() -> None:
            _bootstrap_schema(conn)
            if own:
                conn.commit()

        _retry_locked(_run)
        _initialized_paths.add(path_key)

    if own:
        conn.close()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def broker_account_id(conn: sqlite3.Connection, broker_code: str, label: str = "Основной") -> int:
    row = conn.execute(
        """
        SELECT a.id FROM accounts a
        JOIN brokers b ON b.id = a.broker_id
        WHERE b.code = ? AND a.label = ?
        """,
        (broker_code, label),
    ).fetchone()
    if not row:
        raise ValueError(f"account not found: {broker_code}/{label}")
    return int(row["id"])


def ensure_account(conn: sqlite3.Connection, broker_code: str, label: str = "Основной") -> int:
    conn.execute(
        """
        INSERT INTO accounts (broker_id, label, currency)
        SELECT id, ?, 'RUB' FROM brokers WHERE code = ?
        ON CONFLICT(broker_id, label) DO NOTHING
        """,
        (label, broker_code),
    )
    return broker_account_id(conn, broker_code, label)


def upsert_instrument(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    isin: str | None = None,
    name: str | None = None,
    asset_class: str = "stock",
    is_liquidity_fund: bool = False,
) -> int:
    ticker = ticker.strip().upper()
    conn.execute(
        """
        INSERT INTO instruments (ticker, isin, name, asset_class, is_liquidity_fund)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            isin=COALESCE(excluded.isin, instruments.isin),
            name=COALESCE(excluded.name, instruments.name),
            asset_class=excluded.asset_class,
            is_liquidity_fund=excluded.is_liquidity_fund
        """,
        (ticker, isin, name, asset_class, int(is_liquidity_fund)),
    )
    row = conn.execute("SELECT id FROM instruments WHERE ticker=?", (ticker,)).fetchone()
    return int(row["id"])


def insert_transaction(
    conn: sqlite3.Connection,
    *,
    account_id: int,
    instrument_id: int | None,
    tx_date: str,
    tx_type: str,
    quantity: float | None = None,
    price: float | None = None,
    amount: float | None = None,
    fee: float = 0.0,
    currency: str = "RUB",
    external_id: str | None = None,
    note: str | None = None,
) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO transactions (
                account_id, instrument_id, tx_date, tx_type, quantity, price, amount,
                fee, currency, external_id, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                instrument_id,
                tx_date,
                tx_type,
                quantity,
                price,
                amount,
                fee,
                currency,
                external_id,
                note,
                _now_iso(),
            ),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def insert_cashflow(
    conn: sqlite3.Connection,
    *,
    account_id: int,
    flow_date: str,
    amount: float,
    flow_type: str,
    note: str | None = None,
    external_id: str | None = None,
) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO cashflows (account_id, flow_date, amount, flow_type, note, external_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, flow_date, amount, flow_type, note, external_id, _now_iso()),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def upsert_manual_position(
    conn: sqlite3.Connection,
    *,
    account_id: int,
    instrument_id: int,
    quantity: float,
    avg_price: float | None = None,
    note: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO manual_positions (account_id, instrument_id, quantity, avg_price, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, instrument_id) DO UPDATE SET
            quantity=excluded.quantity,
            avg_price=COALESCE(excluded.avg_price, manual_positions.avg_price),
            note=COALESCE(excluded.note, manual_positions.note),
            updated_at=excluded.updated_at
        """,
        (account_id, instrument_id, quantity, avg_price, note, _now_iso()),
    )


def list_brokers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM brokers ORDER BY id").fetchall()


def fetch_transactions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT t.*, b.code AS broker_code, b.name AS broker_name, i.ticker, i.name AS instrument_name
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN brokers b ON b.id = a.broker_id
        LEFT JOIN instruments i ON i.id = t.instrument_id
        ORDER BY t.tx_date, t.id
        """
    ).fetchall()


def fetch_cashflows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.*, b.code AS broker_code, b.name AS broker_name
        FROM cashflows c
        JOIN accounts a ON a.id = c.account_id
        JOIN brokers b ON b.id = a.broker_id
        ORDER BY c.flow_date, c.id
        """
    ).fetchall()
