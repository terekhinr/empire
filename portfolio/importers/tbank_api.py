"""Синхронизация Т-Банк Invest API (REST, read-only токен)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from portfolio.config import TBANK_ACCOUNT_ID, TBANK_TOKEN
from portfolio.asset_classify import classify_asset
from portfolio.db import broker_account_id, ensure_account, insert_cashflow, insert_transaction, upsert_instrument

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


def _account_label(acc: dict) -> str:
    name = str(acc.get("name") or "").strip()
    if name:
        return name[:80]
    mapping = {
        "ACCOUNT_TYPE_TINKOFF": "Брокерский",
        "ACCOUNT_TYPE_TINKOFF_IIS": "ИИС",
        "ACCOUNT_TYPE_INVEST_BOX": "Инвесткопилка",
    }
    return mapping.get(str(acc.get("type") or ""), str(acc.get("id") or "Основной")[:12])


def list_open_accounts() -> list[dict]:
    accounts = []
    for acc in list_accounts():
        status = str(acc.get("status") or "")
        if status and status not in ("ACCOUNT_STATUS_OPEN", "ACCOUNT_STATUS_NEW"):
            continue
        accounts.append(acc)
    return accounts


def resolve_sync_accounts() -> list[tuple[str, str]]:
    """[(external_id, label)] — все открытые счета, либо один из PORTFOLIO_TBANK_ACCOUNT_ID."""
    accounts = list_open_accounts()
    if TBANK_ACCOUNT_ID:
        accounts = [a for a in accounts if a.get("id") == TBANK_ACCOUNT_ID] or accounts[:1]
    if not accounts:
        raise RuntimeError("Т-Банк: нет доступных счетов")
    if len(accounts) == 1:
        return [(accounts[0]["id"], "Основной")]
    seen: dict[str, int] = {}
    out: list[tuple[str, str]] = []
    for acc in accounts:
        label = _account_label(acc)
        n = seen.get(label, 0)
        seen[label] = n + 1
        if n:
            label = f"{label} ({n + 1})"
        out.append((acc["id"], label))
    return out


def sync_tbank_positions(
    conn: sqlite3.Connection,
    account_ext: str | None = None,
    account_id: int | None = None,
) -> dict[str, Any]:
    """Текущие позиции из GetPortfolio → manual_positions."""
    from portfolio.db import upsert_manual_position

    if account_ext is None or account_id is None:
        account_ext = resolve_account_id()
        account_id = broker_account_id(conn, "tbank")
    portfolio = _post(
        "tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
        {"accountId": account_ext},
    )
    conn.execute(
        "DELETE FROM manual_positions WHERE account_id=? AND note='tbank_api'",
        (account_id,),
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
    return {"broker": "tbank", "account": account_ext, "positions_updated": updated}


def _sync_tbank_operations(
    conn: sqlite3.Connection,
    account_ext: str,
    account_id: int,
    days_back: int,
) -> dict[str, int]:
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

    added_tx = skipped_tx = added_cf = 0
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
                external_id=f"tbank:cf:{account_ext}:{op_id}",
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
                external_id=f"tbank:cf:{account_ext}:{op_id}",
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
            external_id=f"tbank:tx:{account_ext}:{op_id}",
            note=desc,
        )
        if ok:
            added_tx += 1
        else:
            skipped_tx += 1
    return {
        "operations": len(ops),
        "added_tx": added_tx,
        "skipped_tx": skipped_tx,
        "added_cashflows": added_cf,
    }


def sync_tbank(conn: sqlite3.Connection, days_back: int = 365) -> dict[str, Any]:
    accounts = resolve_sync_accounts()
    totals = {
        "broker": "tbank",
        "accounts": [],
        "added_tx": 0,
        "skipped_tx": 0,
        "added_cashflows": 0,
        "positions_updated": 0,
    }
    for ext_id, label in accounts:
        account_id = ensure_account(conn, "tbank", label=label)
        ops = _sync_tbank_operations(conn, ext_id, account_id, days_back)
        pos = sync_tbank_positions(conn, ext_id, account_id)
        totals["accounts"].append({"id": ext_id, "label": label, **ops, **pos})
        totals["added_tx"] += ops["added_tx"]
        totals["skipped_tx"] += ops["skipped_tx"]
        totals["added_cashflows"] += ops["added_cashflows"]
        totals["positions_updated"] += pos.get("positions_updated", 0)
    return totals


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
