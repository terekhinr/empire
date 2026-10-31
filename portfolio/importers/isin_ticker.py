"""ISIN / имя → тикер MOEX (кэш + ISS API)."""

from __future__ import annotations

import logging
import re

import requests

log = logging.getLogger(__name__)
_CACHE: dict[str, str | None] = {}
_PREFERRED_BOARDS = frozenset({"TQBR", "TQTF", "TQOB", "TQCB", "CETS", "SMAL"})

# Короткие имена из брокерских отчётов, которые ISS ищет слишком широко
_NAME_ALIASES = {
    "СБЕРБАНК": "SBER",
    "ГАЗПРНЕФТЬ": "SIBN",
    "РОСНЕФТЬ": "ROSN",
    "ПОЛЮС": "PLZL",
    "ЗАЙМЕР": "ZAYM",
    "ФОСАГРО": "PHOR",
    "ЮЖУРАЛЗОЛОТО": "UGLD",
    "МД": "MDMG",
}


def _norm_key(q: str) -> str:
    return q.strip().upper().rstrip("@")


def looks_like_isin(ticker: str) -> bool:
    return bool(re.match(r"^RU[A-Z0-9]{9,12}$", (ticker or "").strip().upper()))


def isin_to_ticker(isin: str) -> str | None:
    isin = (isin or "").strip().upper()
    if not isin:
        return None
    return query_to_ticker(isin)


def _search_query(raw: str) -> str:
    s = re.sub(r"\s+(ао|ап|обл)\S*$", "", raw.strip(), flags=re.IGNORECASE)
    return s.strip() or raw.strip()


def query_to_ticker(query: str) -> str | None:
    """Ищет SECID по ISIN, тикеру или краткому имени (ГАЗПРНЕФТЬ → SIBN)."""
    raw = (query or "").strip()
    if not raw:
        return None
    key = _norm_key(raw)
    if key in _CACHE:
        return _CACHE[key]
    if key in _NAME_ALIASES:
        _CACHE[key] = _NAME_ALIASES[key]
        return _CACHE[key]
    q = _search_query(raw)
    try:
        r = requests.get(
            "https://iss.moex.com/iss/securities.json",
            params={"q": q.rstrip("@"), "iss.meta": "off", "iss.only": "securities"},
            timeout=12,
        )
        r.raise_for_status()
        block = r.json().get("securities") or {}
        cols = [str(c).lower() for c in (block.get("columns") or [])]
        ranked: list[tuple[int, str]] = []
        for row in block.get("data") or []:
            rec = {cols[i]: row[i] for i in range(min(len(cols), len(row)))}
            if rec.get("is_traded") not in (1, "1", True):
                continue
            secid = str(rec.get("secid") or "").upper()
            if not secid or secid.startswith("FIX"):
                continue
            board = str(rec.get("primary_boardid") or "").upper()
            group = str(rec.get("group") or "").lower()
            typ = str(rec.get("type") or "").lower()
            row_isin = str(rec.get("isin") or "").upper()
            rank = 50
            if key == secid or key == row_isin or _norm_key(q) == secid:
                rank -= 40
            if group.startswith("stock_shares") or group.startswith("stock_etf"):
                rank -= 25
            elif "bond" in group or "bond" in typ:
                rank += 15
            if board == "TQBR":
                rank -= 10
            elif board in _PREFERRED_BOARDS:
                rank -= 4
            if re.match(r"^[A-Z]{2,12}\d{0,4}[A-Z]?$", secid) and not secid.startswith("RU"):
                rank -= 8
            ranked.append((rank, secid))
        ranked.sort()
        if ranked:
            _CACHE[key] = ranked[0][1]
            return _CACHE[key]
        rows = block.get("data") or []
        if rows:
            secid = str(rows[0][0]).upper()
            if not secid.startswith("FIX"):
                _CACHE[key] = secid
                return secid
    except Exception as exc:
        log.debug("query %s: %s", raw, exc)
    _CACHE[key] = None
    return None
