"""Portfolio Snowball metrics without live MOEX."""

from __future__ import annotations

from datetime import date, timedelta

from portfolio import db as pdb
from portfolio.asset_classify import classify_asset
from portfolio.calc import metrics as met
from portfolio.calc.positions import realized_pnl
from portfolio.prices.moex import bond_dirty_price, cache_prices, get_cached_or_fetch


def test_bond_dirty_price():
    assert abs(bond_dirty_price(53.39, 1000, 17.7) - 551.6) < 0.01


def test_ofz_classified_as_bond():
    cls, _ = classify_asset("SU26238RMFS4", name="ОФЗ-ПД 26238")
    assert cls == "bond"
    cls, liq = classify_asset("LQDT")
    assert cls == "liquidity" and liq


def test_metrics_value_and_pnl(tmp_db, monkeypatch):
    monkeypatch.setattr(met, "get_cached_or_fetch", lambda conn, tickers, force=False, **k: {"SBER": 300.0})
    monkeypatch.setattr(met, "quote_dates", lambda conn, tickers: {"SBER": date.today().isoformat()})

    with pdb.db_session() as conn:
        pdb.init_db(conn)
        iid = pdb.upsert_instrument(conn, "SBER", name="Сбербанк", asset_class="stock")
        aid = pdb.broker_account_id(conn, "alfa")
        pdb.upsert_manual_position(
            conn, account_id=aid, instrument_id=iid, quantity=10, avg_price=250
        )
        pdb.insert_cashflow(
            conn,
            account_id=aid,
            flow_date="2024-01-01",
            amount=2500,
            flow_type="deposit",
            external_id="t1",
        )
        m, rows = met.compute_metrics(conn)

    assert len(rows) == 1
    assert m.total_value == 3000
    assert m.cost_basis == 2500
    assert m.priced_count == 1
    assert not m.unpriced
    assert m.price_as_of == date.today().isoformat()
    assert abs((m.profit_pct or 0) - 20.0) < 0.05
    assert abs((m.unrealized_pnl_pct or 0) - 20.0) < 0.05


def test_unpriced_listed(tmp_db, monkeypatch):
    monkeypatch.setattr(met, "get_cached_or_fetch", lambda conn, tickers, force=False, **k: {})
    monkeypatch.setattr(met, "quote_dates", lambda conn, tickers: {})
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        iid = pdb.upsert_instrument(conn, "SBER", name="Сбербанк")
        aid = pdb.broker_account_id(conn, "vtb")
        pdb.upsert_manual_position(conn, account_id=aid, instrument_id=iid, quantity=1, avg_price=100)
        m, rows = met.compute_metrics(conn)
    assert m.unpriced == ["SBER"]
    assert m.priced_count == 0
    assert rows[0]["market_value"] is None


def test_realized_pnl_avg(tmp_db):
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        iid = pdb.upsert_instrument(conn, "GAZP")
        aid = pdb.broker_account_id(conn, "tbank")
        pdb.insert_transaction(
            conn,
            account_id=aid,
            instrument_id=iid,
            tx_date="2024-01-01",
            tx_type="buy",
            quantity=10,
            price=100,
            amount=1000,
            external_id="b1",
        )
        pdb.insert_transaction(
            conn,
            account_id=aid,
            instrument_id=iid,
            tx_date="2024-06-01",
            tx_type="sell",
            quantity=4,
            price=150,
            amount=600,
            external_id="s1",
        )
        assert abs(realized_pnl(conn) - 200.0) < 0.01


def test_twr_two_snapshots(tmp_db):
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        d0 = (date.today() - timedelta(days=40)).isoformat()
        conn.execute(
            """
            INSERT INTO daily_snapshots (snap_date, total_value, payload_json, created_at)
            VALUES (?, 1000, '{}', ?)
            """,
            (d0, d0),
        )
        twr, ann = met.compute_twr(conn, 1100)
    assert twr is not None
    assert abs(twr - 0.10) < 0.001
    assert ann is not None


def test_cache_today_skips_fetch(tmp_db, monkeypatch):
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("should not fetch")

    monkeypatch.setattr("portfolio.prices.moex.fetch_prices", boom)
    today = date.today().isoformat()
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        cache_prices(conn, {"SBER": 275.0}, today, source="moex")
        got = get_cached_or_fetch(conn, ["SBER"], force=False)
    assert got["SBER"] == 275.0
    assert called["n"] == 0


def test_network_false_uses_stale_cache(tmp_db, monkeypatch):
    monkeypatch.setattr(
        "portfolio.prices.moex.fetch_prices",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no network")),
    )
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        conn.execute(
            "INSERT INTO price_cache (ticker, price_date, price, source) VALUES (?,?,?,?)",
            ("SBER", "2026-01-01", 100.0, "gpb_report"),
        )
        got = get_cached_or_fetch(conn, ["SBER"], force=False, network=False)
    assert got["SBER"] == 100.0


def test_stale_report_price_refetched(tmp_db, monkeypatch):
    monkeypatch.setattr(
        "portfolio.prices.moex.fetch_prices",
        lambda tickers: {t.upper(): 280.0 for t in tickers},
    )
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        conn.execute(
            "INSERT INTO price_cache (ticker, price_date, price, source) VALUES (?,?,?,?)",
            ("SBER", "2026-01-01", 100.0, "gpb_report"),
        )
        got = get_cached_or_fetch(conn, ["SBER"], force=False)
    assert got["SBER"] == 280.0


def test_query_sber_prefers_share():
    from portfolio.importers.isin_ticker import _CACHE, query_to_ticker

    _CACHE.clear()
    assert query_to_ticker("Сбербанк ао") == "SBER"
    _CACHE.clear()
    assert query_to_ticker("ГАЗПРНЕФТЬ") == "SIBN"
