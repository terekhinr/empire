from fastapi.testclient import TestClient

from portfolio.auth import COOKIE_NAME, session_token
from sauron.nav import TITLES
from web_app import app


def test_hub_head_does_not_reset():
    client = TestClient(app)
    r = client.head("/hub/login")
    assert r.status_code == 200
    assert (r.headers.get("content-type") or "").startswith("text/plain")
    assert not r.content
    r2 = client.head("/hub/portfolio", follow_redirects=False)
    assert r2.status_code == 200
    assert (r2.headers.get("content-type") or "").startswith("text/plain")
    assert not r2.content
    health = client.head("/api/health")
    assert health.status_code == 200


def test_hub_login_is_html_not_streamlit():
    client = TestClient(app)
    r = client.get("/hub/login")
    assert r.status_code == 200
    assert "Око Саурона" in r.text
    assert "Пароль" in r.text
    assert "Streamlit" not in r.text
    assert "<form" in r.text


def test_hub_root_redirects_to_login():
    client = TestClient(app)
    r = client.get("/hub/", follow_redirects=False)
    assert r.status_code in (303, 307)
    assert "/hub/login" in r.headers.get("location", "")


def test_hub_login_success_goes_to_monitoring(tmp_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_DASHBOARD_PASSWORD", "test-secret")
    client = TestClient(app)
    r = client.post("/hub/login", data={"password": "test-secret"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location", "").endswith("/hub/monitoring")
    assert "empire_pf" in r.headers.get("set-cookie", "")


def test_hub_authed_has_all_sidebar_tabs(tmp_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_DASHBOARD_PASSWORD", "test-secret")
    from portfolio.calc import metrics as met

    monkeypatch.setattr(met, "get_cached_or_fetch", lambda conn, tickers, force=False, **k: {})
    monkeypatch.setattr(met, "quote_dates", lambda conn, tickers: {})

    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, session_token("test-secret"))
    r = client.get("/hub/monitoring")
    assert r.status_code == 200
    assert "Око Саурона" in r.text
    assert "Мониторинг" in r.text
    for slug in TITLES:
        pr = client.get(f"/hub/{slug}")
        assert pr.status_code == 200, (slug, pr.status_code, pr.text[:500])
        assert "Око Саурона" in pr.text
        assert 'class="side"' in pr.text
        assert f'href="/hub/{slug}"' in pr.text
        assert "не собралась" not in pr.text
    assert "Streamlit" not in r.text


def test_hub_kills_streamlit_sw():
    client = TestClient(app)
    r = client.get("/hub/sw.js")
    assert r.status_code == 200
    assert "unregister" in r.text
    st = client.get("/hub/_stcore/stream")
    assert st.status_code == 204


def test_hub_portfolio_page_has_snowball(tmp_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_DASHBOARD_PASSWORD", "test-secret")
    from portfolio import db as pdb
    from portfolio.calc import metrics as met

    monkeypatch.setattr(met, "get_cached_or_fetch", lambda conn, tickers, force=False, **k: {"SBER": 300.0})
    monkeypatch.setattr(met, "quote_dates", lambda conn, tickers: {"SBER": "2026-09-01"})
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        iid = pdb.upsert_instrument(conn, "SBER", name="Сбербанк")
        aid = pdb.broker_account_id(conn, "alfa")
        pdb.upsert_manual_position(conn, account_id=aid, instrument_id=iid, quantity=10, avg_price=250)

    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, session_token("test-secret"))
    r = client.get("/hub/portfolio")
    assert r.status_code == 200
    assert "Ключевые показатели" in r.text
    assert 'for="pt-hold"' in r.text
    assert "Активы" in r.text
    assert 'id="pt-hold"' in r.text
    assert "#pt-hold:checked" in r.text.split("<style>")[1].split("</style>")[0]
    assert "data-filter-broker" in r.text
    assert "SBER" in r.text
    assert "conic-gradient" not in r.text
    assert "color-scheme" in r.text
    assert 'class="side"' in r.text


def test_refresh_prices_does_not_hold_db_during_moex(tmp_db, monkeypatch):
    import threading
    import time

    from portfolio import db as pdb
    from portfolio.sync import refresh_prices
    from portfolio.web_routes import _load, invalidate_bundle

    with pdb.db_session() as conn:
        pdb.init_db(conn)
        iid = pdb.upsert_instrument(conn, "SBER", name="Сбербанк")
        aid = pdb.broker_account_id(conn, "alfa")
        pdb.upsert_manual_position(conn, account_id=aid, instrument_id=iid, quantity=10, avg_price=250)

    started = threading.Event()
    release = threading.Event()

    def fake_fetch(tickers):
        started.set()
        release.wait(timeout=5)
        return {"SBER": 300.0}

    monkeypatch.setattr("portfolio.prices.moex.fetch_prices", fake_fetch)
    invalidate_bundle()
    t = threading.Thread(target=refresh_prices, kwargs={"force": True})
    t.start()
    assert started.wait(timeout=2)
    t0 = time.perf_counter()
    _load()
    dt = time.perf_counter() - t0
    release.set()
    t.join(timeout=5)
    assert dt < 1.5, dt
