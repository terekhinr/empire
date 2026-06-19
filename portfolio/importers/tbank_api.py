"""Синхронизация Т-Банк Invest API (REST, read-only токен)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from portfolio.config import TBANK_ACCOUNT_ID, TBANK_TOKEN
from portfolio.asset_classify import classify_asset
from portfolio.db import broker_account_id, insert_cashflow, insert_transaction, upsert_instrument

log = logging.getLogger(__name__)

REST_BASE = "https://invest-public-api.tinkoff.ru/rest"
_FIGI_CACHE: dict[str, str | None] = {}


def _headers() -> dict[str, str]:
    if not TBANK_TOKEN:
        raise RuntimeError("PORTFOLIO_TBANK_TOKEN не задан в .env")
    return {"Authorization": f"Bearer {TBANK_TOKEN}", "Content-Type": "application/json"}


def _post(path: str, body: dict) -> dict:
    url = f"{REST_BASE}/{path}"
    r = requests.post(url, headers=_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def list_accounts() -> list[dict]:
    data = _post("tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts", {})
    return data.get("accounts", [])


def resolve_account_id() -> str:
    if TBANK_ACCOUNT_ID:
        return TBANK_ACCOUNT_ID
    accounts = list_accounts()
    if not accounts:
        raise RuntimeError("Т-Банк: нет доступных счетов")
    # предпочитаем брокерский счёт (не ИИС) если можно
    for acc in accounts:
        if acc.get("type") == "ACCOUNT_TYPE_TINKOFF":
            return acc["id"]
    return accounts[0]["id"]


def _money_to_float(m: Any) -> float:
    if m is None:
        return 0.0
    if isinstance(m, (int, float)):
        return float(m)
    if isinstance(m, str):
        try:
            return float(m.replace(",", "."))
        except ValueError:
            return 0.0
    if not isinstance(m, dict):
        return 0.0
    units = float(m.get("units", 0) or 0)
    nano = float(m.get("nano", 0) or 0)
    return units + nano / 1_000_000_000


def _quotation_to_float(q: Any) -> float | None:
    if q is None:
        return None
    val = _money_to_float(q)
    return val if val != 0.0 else None


def figi_to_ticker(figi: str) -> str | None:
    if not figi:
        return None
    if figi in _FIGI_CACHE:
        return _FIGI_CACHE[figi]
    try:
        data = _post(
            "tinkoff.public.invest.api.contract.v1.InstrumentsService/GetInstrumentBy",
            {"idType": "INSTRUMENT_ID_TYPE_FIGI", "id": figi},
        )
        inst = data.get("instrument", {})
        ticker = inst.get("ticker") or None
    except Exception as exc:
        log.debug("figi %s: %s", figi, exc)
        ticker = None
    _FIGI_CACHE[figi] = ticker
    return ticker


def sync_tbank_positions(conn: sqlite3.Connection) -> dict[str, Any]:
    """Текущие позиции из GetPortfolio → manual_positions (надёжнее для пассивного счёта)."""
    from portfolio.db import upsert_manual_position

    account_ext = resolve_account_id()
    account_id = broker_account_id(conn, "tbank")
    portfolio = _post(
        "tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
        {"accountId": account_ext},
    )
    updated = 0
    for pos in portfolio.get("positions", []):
        figi = pos.get("figi", "")
        ticker = figi_to_ticker(figi) or figi[:12]
        if not ticker:
            continue
        qty = _quotation_to_float(pos.get("quantity")) or 0.0
        if qty <= 0:
            continue
        if ticker in ("RUB000UTSTOM", "USD000UTSTOM", "EUR000UTSTOM"):
            continue
        avg = _money_to_float(pos.get("averagePositionPrice"))
        inst_type = pos.get("instrumentType", "")
        asset_class, is_liq = classify_asset(ticker, instrument_type=inst_type)
        iid = upsert_instrument(
            conn,
            ticker,
            asset_class=asset_class,
            is_liquidity_fund=is_liq,
        )
        upsert_manual_position(
            conn,
            account_id=account_id,
            instrument_id=iid,
            quantity=qty,
            avg_price=avg or None,
            note="tbank_api",
        )
        updated += 1
    return {"broker": "tbank", "positions_updated": updated}


def sync_tbank(conn: sqlite3.Connection, days_back: int = 365) -> dict[str, Any]:
    account_ext = resolve_account_id()
    account_id = broker_account_id(conn, "tbank")
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=days_back)).isoformat()
    to = now.isoformat()

    ops = _post(
        "tinkoff.public.invest.api.contract.v1.OperationsService/GetOperations",
        {
            "accountId": account_ext,
            "from": frm,
            "to": to,
            "state": "OPERATION_STATE_EXECUTED",
        },
    ).get("operations", [])

    added_tx = 0
    skipped_tx = 0
    added_cf = 0

    for op in ops:
        op_id = op.get("id")
        if not op_id:
            continue
        op_date = (op.get("date") or "")[:10]
        op_type = op.get("operationType", "")
        figi = op.get("figi") or ""
        instrument_type = op.get("instrumentType", "")
        payment = _money_to_float(op.get("payment"))
        price = _quotation_to_float(op.get("price"))
        qty = _quotation_to_float(op.get("quantity")) or 0.0

        desc = op.get("description") or ""
        symbol = figi_to_ticker(figi) or _guess_ticker(desc, op.get("instrumentUid", ""))

        if op_type in ("OPERATION_TYPE_INPUT", "OPERATION_TYPE_INP_MULTI"):
            if insert_cashflow(
                conn,
                account_id=account_id,
                flow_date=op_date,
                amount=abs(payment),
                flow_type="deposit",
                note=desc,
                external_id=f"tbank:cf:{op_id}",
            ):
                added_cf += 1
            continue

        if op_type in ("OPERATION_TYPE_OUTPUT", "OPERATION_TYPE_OUT_MULTI"):
            if insert_cashflow(
                conn,
                account_id=account_id,
                flow_date=op_date,
                amount=abs(payment),
                flow_type="withdrawal",
                note=desc,
                external_id=f"tbank:cf:{op_id}",
            ):
                added_cf += 1
            continue

        if not symbol:
            continue

        tx_type = _map_operation(op_type, payment)
        asset_class, is_liq = classify_asset(symbol, name=desc, instrument_type=instrument_type)
        iid = upsert_instrument(
            conn,
            symbol,
            name=desc[:120] if desc else None,
            asset_class=asset_class,
            is_liquidity_fund=is_liq,
        )
        ok = insert_transaction(
            conn,
            account_id=account_id,
            instrument_id=iid,
            tx_date=op_date,
            tx_type=tx_type,
            quantity=abs(qty) if qty else None,
            price=price,
            amount=abs(payment) if payment else None,
            external_id=f"tbank:tx:{op_id}",
            note=desc,
        )
        if ok:
            added_tx += 1
        else:
            skipped_tx += 1

    pos_result = sync_tbank_positions(conn)

    return {
        "broker": "tbank",
        "account_id": account_ext,
        "operations": len(ops),
        "added_tx": added_tx,
        "skipped_tx": skipped_tx,
        "added_cashflows": added_cf,
        "positions_updated": pos_result.get("positions_updated", 0),
    }


def _guess_ticker(description: str, uid: str) -> str | None:
    import re

    for token in description.upper().replace("«", " ").replace("»", " ").split():
        if re.match(r"^[A-Z]{2,10}\d?$", token):
            return token
    if uid:
        return uid[:12]
    return None


def _map_operation(op_type: str, payment: float) -> str:
    if "BUY" in op_type:
        return "buy"
    if "SELL" in op_type:
        return "sell"
    if "DIVIDEND" in op_type or "COUPON" in op_type:
        return "dividend_reinvest" if payment <= 0 else "dividend"
    return "buy"
