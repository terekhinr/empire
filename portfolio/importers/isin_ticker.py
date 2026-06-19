"""ISIN → тикер MOEX (кэш + ISS API)."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)
_CACHE: dict[str, str | None] = {}


def isin_to_ticker(isin: str) -> str | None:
    isin = isin.strip().upper()
    if not isin:
        return None
    if isin in _CACHE:
        return _CACHE[isin]
    try:
        r = requests.get(
            "https://iss.moex.com/iss/securities.json",
            params={"q": isin, "iss.meta": "off", "iss.only": "securities"},
            timeout=12,
        )
        r.raise_for_status()
        rows = r.json().get("securities", {}).get("data", [])
        for row in rows:
            if len(row) >= 3 and str(row)[0:2] != "":  # noqa: SIM114
                secid = row[0]
                row_isin = row[2] if len(row) > 2 else ""
                if str(row_isin).upper() == isin and secid:
                    _CACHE[isin] = str(secid).upper()
                    return _CACHE[isin]
        if rows:
            _CACHE[isin] = str(rows[0][0]).upper()
            return _CACHE[isin]
    except Exception as exc:
        log.debug("isin %s: %s", isin, exc)
    _CACHE[isin] = None
    return None
