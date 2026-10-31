"""Метрики портфеля в стиле Snowball Income."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from portfolio.calc.positions import PositionRow, compute_positions, enrich_with_prices, realized_pnl
from portfolio.asset_classify import ASSET_CLASS_LABELS, ASSET_CLASS_ORDER
from portfolio.calc.xirr import compute_xirr
from portfolio.calc.snapshots import load_snapshot_history
from portfolio.prices.moex import get_cached_or_fetch, quote_dates

_ACCOUNT_TARGET_PREFIX = "portfolio_target_value:"


def _load_account_targets(conn: sqlite3.Connection) -> dict[tuple[str, str], float]:
    """Целевая стоимость счёта из settings: portfolio_target_value:{broker}:{account}."""
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{_ACCOUNT_TARGET_PREFIX}%",),
    ).fetchall()
    out: dict[tuple[str, str], float] = {}
    for row in rows:
        key = str(row["key"])
        if not key.startswith(_ACCOUNT_TARGET_PREFIX):
            continue
        rest = key[len(_ACCOUNT_TARGET_PREFIX) :]
        if ":" not in rest:
            continue
        broker_code, account_label = rest.split(":", 1)
        try:
            out[(broker_code, account_label)] = float(row["value"])
        except (TypeError, ValueError):
            continue
    return out


def _account_scale_factors(
    rows: list[dict[str, Any]], targets: dict[tuple[str, str], float]
) -> dict[tuple[str, str], float]:
    """Динамический коэффициент: target / текущая оценка по счёту."""
    if not targets:
        return {}
    raw: dict[tuple[str, str], float] = {}
    for r in rows:
        key = (str(r.get("broker_code") or ""), str(r.get("account_label") or ""))
        if key not in targets or r.get("market_value") is None:
            continue
        raw[key] = raw.get(key, 0.0) + float(r["market_value"])
    scales: dict[tuple[str, str], float] = {}
    for key, target in targets.items():
        base = raw.get(key, 0.0)
        if base > 0:
            scales[key] = target / base
    return scales


def _apply_account_scales(
    rows: list[dict[str, Any]], scales: dict[tuple[str, str], float]
) -> None:
    if not scales:
        return
    for r in rows:
        key = (str(r.get("broker_code") or ""), str(r.get("account_label") or ""))
        mult = scales.get(key)
        if not mult or r.get("market_value") is None:
            continue
        mv = float(r["market_value"]) * mult
        r["market_value"] = mv
        cost = r.get("cost_basis")
        if cost is not None:
            cost_f = float(cost)
            pnl = mv - cost_f
            r["pnl"] = pnl
            r["pnl_pct"] = (pnl / cost_f * 100) if cost_f > 0 else None
        lp = r.get("last_price")
        if lp is not None:
            r["last_price"] = float(lp) * mult


@dataclass
class SnowballMetrics:
    total_value: float = 0.0
    cost_basis: float = 0.0
    net_invested: float = 0.0
    profit_abs: float = 0.0
    profit_pct: float | None = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float | None = None
    xirr: float | None = None
    dividends: float = 0.0
    coupons: float = 0.0
    day_change_abs: float | None = None
    day_change_pct: float | None = None
    month_change_abs: float | None = None
    month_change_pct: float | None = None
    ytd_change_abs: float | None = None
    ytd_change_pct: float | None = None
    positions_count: int = 0
    priced_count: int = 0
    realized_pnl: float = 0.0
    twr_pct: float | None = None
    twr_annual_pct: float | None = None
    yield_on_cost_pct: float | None = None
    analyzed_at: str = ""
    price_as_of: str = ""
    unpriced: list[str] = field(default_factory=list)
    by_broker: list[dict[str, Any]] = field(default_factory=list)
    by_account: list[dict[str, Any]] = field(default_factory=list)
    by_class: list[dict[str, Any]] = field(default_factory=list)


def _prices_on_date(conn: sqlite3.Connection, tickers: list[str], on: date) -> dict[str, float]:
    out: dict[str, float] = {}
    d = on.isoformat()
    for t in tickers:
        row = conn.execute(
            """
            SELECT price FROM price_cache
            WHERE ticker=? AND price_date <= ?
            ORDER BY price_date DESC LIMIT 1
            """,
            (t, d),
        ).fetchone()
        if row:
            out[t] = float(row["price"])
    return out


def _portfolio_value(positions: list[PositionRow], prices: dict[str, float]) -> float:
    total = 0.0
    for p in positions:
        px = prices.get(p.ticker)
        if px is not None:
            total += px * p.quantity
    return total


def _net_invested(conn: sqlite3.Connection) -> float:
    rows = conn.execute(
        "SELECT flow_type, SUM(amount) AS s FROM cashflows GROUP BY flow_type"
    ).fetchall()
    totals = {r["flow_type"]: float(r["s"]) for r in rows}
    deposits = totals.get("deposit", 0.0)
    withdrawals = totals.get("withdrawal", 0.0) + totals.get("dividend_withdrawn", 0.0)
    return max(0.0, deposits - withdrawals)


def _income_from_transactions(conn: sqlite3.Connection) -> tuple[float, float]:
    rows = conn.execute(
        """
        SELECT tx_type, SUM(COALESCE(amount, quantity * price, 0)) AS s
        FROM transactions
        WHERE tx_type IN ('dividend', 'coupon')
        GROUP BY tx_type
        """
    ).fetchall()
    totals = {r["tx_type"]: float(r["s"] or 0) for r in rows}
    return totals.get("dividend", 0.0), totals.get("coupon", 0.0)


def _change(current: float, past: float | None) -> tuple[float | None, float | None]:
    if past is None or past <= 0:
        return None, None
    diff = current - past
    return diff, (diff / past) * 100


def _snapshot_value_on(conn: sqlite3.Connection, ref: date) -> float | None:
    row = conn.execute(
        """
        SELECT total_value FROM daily_snapshots
        WHERE snap_date <= ? ORDER BY snap_date DESC LIMIT 1
        """,
        (ref.isoformat(),),
    ).fetchone()
    if row:
        return float(row["total_value"])
    hist = load_snapshot_history(conn)
    if not hist:
        return None
    key = ref.strftime("%Y-%m")
    candidates = [h for h in hist if h["month"] <= key]
    if candidates:
        return float(candidates[-1]["total_value"])
    return None


def save_daily_snapshot(conn: sqlite3.Connection, total: float, payload: dict) -> None:
    import json
    from datetime import datetime, timezone

    today = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO daily_snapshots (snap_date, total_value, payload_json, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(snap_date) DO UPDATE SET
            total_value=excluded.total_value,
            payload_json=excluded.payload_json,
            created_at=excluded.created_at
        """,
        (
            today,
            total,
            json.dumps(payload, ensure_ascii=False),
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        ),
    )


def _net_cf_between(conn: sqlite3.Connection, start: date, end: date) -> float:
    rows = conn.execute(
        """
        SELECT flow_type, SUM(amount) AS s FROM cashflows
        WHERE flow_date > ? AND flow_date <= ?
        GROUP BY flow_type
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    cf = 0.0
    for r in rows:
        s = float(r["s"] or 0)
        if r["flow_type"] == "deposit":
            cf += s
        elif r["flow_type"] in ("withdrawal", "dividend_withdrawn"):
            cf -= s
    return cf


def compute_twr(conn: sqlite3.Connection, current_value: float) -> tuple[float | None, float | None]:
    """TWR по дневным снимкам + текущая стоимость. Доли (0.12 = 12%)."""
    snaps = conn.execute(
        "SELECT snap_date, total_value FROM daily_snapshots ORDER BY snap_date"
    ).fetchall()
    points: list[tuple[date, float]] = [
        (date.fromisoformat(str(r["snap_date"])[:10]), float(r["total_value"])) for r in snaps
    ]
    today = date.today()
    if not points or points[-1][0] != today:
        points.append((today, current_value))
    if len(points) < 2:
        return None, None
    product = 1.0
    used = 0
    for (d0, v0), (d1, v1) in zip(points, points[1:]):
        if v0 <= 0:
            continue
        cf = _net_cf_between(conn, d0, d1)
        product *= 1.0 + (v1 - v0 - cf) / v0
        used += 1
    if used == 0:
        return None, None
    twr = product - 1.0
    days = (points[-1][0] - points[0][0]).days
    ann = None
    if days >= 30 and twr > -0.999:
        ann = (1.0 + twr) ** (365.0 / days) - 1.0
    return twr, ann


def compute_metrics(
    conn: sqlite3.Connection, *, force_prices: bool = False, live_prices: bool = True
) -> tuple[SnowballMetrics, list[dict[str, Any]]]:
    from datetime import datetime, timezone

    positions = compute_positions(conn)
    tickers = [p.ticker for p in positions]
    prices = get_cached_or_fetch(
        conn, tickers, force=force_prices, network=live_prices or force_prices
    )
    qdates = quote_dates(conn, tickers)
    rows = enrich_with_prices(positions, prices, qdates)

    # Подгонка к стоимости из приложения брокера: целевые суммы по счетам
    # (пересчитываются каждый раз, чтобы не устаревать при обновлении котировок).
    account_targets = _load_account_targets(conn)
    account_scales = _account_scale_factors(rows, account_targets)
    _apply_account_scales(rows, account_scales)

    total = sum(r["market_value"] or 0 for r in rows)
    cost = sum(r["cost_basis"] or 0 for r in rows)

    m = SnowballMetrics()
    m.total_value = total
    m.cost_basis = cost
    m.positions_count = len(rows)
    m.priced_count = sum(1 for r in rows if r["last_price"] is not None)
    m.net_invested = _net_invested(conn)

    if m.net_invested > 0:
        m.profit_abs = total - m.net_invested
        m.profit_pct = (m.profit_abs / m.net_invested) * 100
    elif cost > 0:
        m.profit_abs = total - cost
        m.profit_pct = (m.profit_abs / cost) * 100

    if cost > 0:
        m.unrealized_pnl = total - cost
        m.unrealized_pnl_pct = (m.unrealized_pnl / cost) * 100

    m.xirr = compute_xirr(conn, total)
    m.dividends, m.coupons = _income_from_transactions(conn)
    m.realized_pnl = realized_pnl(conn)
    twr, twr_ann = compute_twr(conn, total)
    m.twr_pct = twr * 100 if twr is not None else None
    m.twr_annual_pct = twr_ann * 100 if twr_ann is not None else None
    income = m.dividends + m.coupons
    if cost > 0 and income:
        m.yield_on_cost_pct = income / cost * 100
    m.unpriced = [r["ticker"] for r in rows if r.get("last_price") is None]
    m.analyzed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    dated = [r.get("price_date") for r in rows if r.get("price_date")]
    m.price_as_of = max(dated) if dated else date.today().isoformat()

    yesterday = date.today() - timedelta(days=1)
    y_prices = _prices_on_date(conn, tickers, yesterday)
    if y_prices:
        past_total = 0.0
        for p in positions:
            px = y_prices.get(p.ticker)
            if px is None:
                continue
            mult = account_scales.get((p.broker_code, p.account_label), 1.0)
            past_total += float(px) * p.quantity * mult
        m.day_change_abs, m.day_change_pct = _change(total, past_total)
    else:
        past_snap = _snapshot_value_on(conn, yesterday)
        m.day_change_abs, m.day_change_pct = _change(total, past_snap)

    month_start = date.today().replace(day=1) - timedelta(days=1)
    month_val = _snapshot_value_on(conn, month_start)
    m.month_change_abs, m.month_change_pct = _change(total, month_val)

    ytd_ref = date(date.today().year - 1, 12, 31)
    ytd_val = _snapshot_value_on(conn, ytd_ref)
    m.ytd_change_abs, m.ytd_change_pct = _change(total, ytd_val)

    for r in rows:
        r["share_pct"] = ((r["market_value"] or 0) / total * 100) if total > 0 else None
        yp = y_prices.get(r["ticker"])
        lp = r["last_price"]
        if yp and lp and yp > 0:
            r["day_change_pct"] = ((lp - yp) / yp) * 100
            r["day_change_abs"] = (lp - yp) * r["quantity"]
        else:
            r["day_change_pct"] = None
            r["day_change_abs"] = None

    broker_agg: dict[str, dict[str, float]] = {}
    for r in rows:
        b = r["broker"]
        st = broker_agg.setdefault(b, {"value": 0.0, "cost": 0.0, "pnl": 0.0})
        st["value"] += r["market_value"] or 0
        st["cost"] += r["cost_basis"] or 0
        st["pnl"] += r["pnl"] or 0
    m.by_broker = [
        {
            "broker": b,
            "value": v["value"],
            "share_pct": (v["value"] / total * 100) if total else 0,
            "cost": v["cost"],
            "pnl": v["pnl"],
            "pnl_pct": (v["pnl"] / v["cost"] * 100) if v["cost"] > 0 else None,
        }
        for b, v in sorted(broker_agg.items(), key=lambda x: -x[1]["value"])
    ]

    account_agg: dict[str, dict[str, Any]] = {}
    for r in rows:
        label = r.get("account_label") or r["broker"]
        key = f"{r['broker']} · {label}"
        st = account_agg.setdefault(key, {"broker": r["broker"], "account": label, "value": 0.0, "cost": 0.0, "pnl": 0.0})
        st["value"] += r["market_value"] or 0
        st["cost"] += r["cost_basis"] or 0
        st["pnl"] += r["pnl"] or 0
    m.by_account = [
        {
            "label": key,
            "broker": v["broker"],
            "account": v["account"],
            "value": v["value"],
            "share_pct": (v["value"] / total * 100) if total else 0,
            "cost": v["cost"],
            "pnl": v["pnl"],
            "pnl_pct": (v["pnl"] / v["cost"] * 100) if v["cost"] > 0 else None,
        }
        for key, v in sorted(account_agg.items(), key=lambda x: -x[1]["value"])
    ]

    class_agg: dict[str, float] = {k: 0.0 for k in ASSET_CLASS_ORDER}
    for r in rows:
        cls = r["asset_class"] if r["asset_class"] in ASSET_CLASS_ORDER else "stock"
        class_agg[cls] = class_agg.get(cls, 0) + (r["market_value"] or 0)
    m.by_class = [
        {
            "class": k,
            "label": ASSET_CLASS_LABELS[k],
            "value": class_agg[k],
            "share_pct": (class_agg[k] / total * 100) if total else 0,
        }
        for k in ASSET_CLASS_ORDER
        if class_agg[k] > 0
    ]

    save_daily_snapshot(conn, total, {"positions": len(rows), "priced": m.priced_count})
    return m, rows


def fmt_rub(val: float | None, signed: bool = False) -> str:
    if val is None:
        return "—"
    s = f"{val:+,.0f}".replace(",", " ") if signed else f"{val:,.0f}".replace(",", " ")
    return f"{s} ₽"


def fmt_xirr(val: float | None) -> str:
    if val is None:
        return "н/д"
    # pyxirr возвращает долю (0.15 = 15%); при кривых cashflow бывают выбросы
    if abs(val) > 3:
        return "н/д*"
    return f"{val * 100:.2f} %"


def fmt_pct(val: float | None, signed: bool = True) -> str:
    if val is None:
        return "—"
    return f"{val:+.2f} %" if signed else f"{val:.2f} %"
