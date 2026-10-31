from fastapi.testclient import TestClient

from portfolio.auth import COOKIE_NAME, session_token
from web_app import app


def test_portfolio_login_page_is_html_not_streamlit():
    client = TestClient(app)
    r = client.get("/portfolio")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Пароль" in r.text
    assert "Streamlit" not in r.text
    assert "<form" in r.text


def test_portfolio_wrong_password():
    client = TestClient(app)
    r = client.post("/portfolio/login", data={"password": "definitely-wrong"}, follow_redirects=False)
    assert r.status_code == 401
    assert "Неверный пароль" in r.text


def test_portfolio_authed_renders_value(tmp_db, monkeypatch):
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
    r = client.get("/portfolio")
    assert r.status_code == 200
    assert "3 000" in r.text.replace("\xa0", " ") or "3000" in r.text.replace(" ", "")
    assert "SBER" in r.text
    assert "Альфа" in r.text
    assert "Ключевые показатели" in r.text
    assert "data-filter-broker" in r.text
    assert "data-filter-class" in r.text
    assert 'for="pt-hold"' in r.text
    assert 'id="pt-hold"' in r.text
    assert "YOC" in r.text
    assert "Себестоимость" in r.text
    assert "По счетам" in r.text
    assert "Нереализ" in r.text
    assert "Сортировка" in r.text
