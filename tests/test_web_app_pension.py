"""Сайт neverretire: health, waitlist, metrika context."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "empire.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    wl = tmp_path / "waitlist.json"
    weekly = tmp_path / "weekly.json"
    monkeypatch.setattr("pension_metrics.WAITLIST_JSON", wl)
    monkeypatch.setattr("pension_metrics.WEEKLY_JSON", weekly)
    monkeypatch.setattr("pension_metrics.BASE_DIR", tmp_path)
    monkeypatch.delenv("YANDEX_METRIKA_ID", raising=False)

    from importlib import reload

    import web_app

    reload(web_app)
    return TestClient(web_app.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["metrika_id_set"] is False


def test_waitlist(client):
    r = client.post("/api/pension/waitlist", json={"email": "test@example.com"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["waitlist_count"] == 1
    r2 = client.post("/api/pension/waitlist", json={"email": "test@example.com"})
    assert r2.json()["waitlist_count"] == 1


def test_buy_page(client):
    book = Path(__file__).resolve().parents[1] / "data" / "book" / "napensiyu_nikogda.json"
    if not book.is_file():
        pytest.skip("book json missing")
    r = client.get("/buy")
    assert r.status_code == 200
    assert "Купить" in r.text or "PDF" in r.text


def test_home_has_waitlist_form(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "waitlist-form" in r.text


def test_metrika_stub_without_id(client):
    r = client.get("/book")
    assert r.status_code == 200
    assert "pensionMetrikaReach" in r.text


def test_gift_consent_checkbox_is_inside_form():
    html = (Path(__file__).resolve().parents[1] / "templates" / "gift.html").read_text(
        encoding="utf-8"
    )
    form_start = html.find('id="gift-form"')
    form_end = html.find("</form>", form_start)
    chunk = html[form_start:form_end]
    assert 'name="consent"' in chunk


def test_buy_page_collects_presale_email(client):
    book = Path(__file__).resolve().parents[1] / "data" / "book" / "napensiyu_nikogda.json"
    if not book.is_file():
        pytest.skip("book json missing")
    r = client.get("/buy")
    assert r.status_code == 200
    assert "buy-waitlist-form" in r.text
    assert "149" in r.text


def test_gift_page_and_api(client):
    r = client.get("/gift")
    assert r.status_code == 200
    assert "gift-form" in r.text
    assert "5 принципов" in r.text
    assert 'name="consent"' in r.text[r.text.find('id="gift-form"') : r.text.find("</form>")]

    r_bad = client.post(
        "/api/pension/gift",
        json={"email": "not-an-email", "consent": True},
    )
    assert r_bad.status_code in (400, 422)

    r_no_consent = client.post(
        "/api/pension/gift",
        json={"email": "gift@example.com", "consent": False},
    )
    assert r_no_consent.status_code == 400

    r_ok = client.post(
        "/api/pension/gift",
        json={
            "email": "gift@example.com",
            "consent": True,
            "utm_source": "tg_seed",
            "utm_campaign": "aug26_gift",
        },
    )
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["ok"] is True
    assert "download_url" in data
    assert data["waitlist_count"] == 1


def test_sitemap_includes_gift(client):
    book = Path(__file__).resolve().parents[1] / "data" / "book" / "napensiyu_nikogda.json"
    if not book.is_file():
        pytest.skip("book json missing")
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "/gift" in r.text


def test_about_telegram_link_when_env_empty(tmp_path, monkeypatch):
    """Пустой PENSION_TG_URL в .env не должен давать href=\"\"."""
    db = tmp_path / "empire.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("PENSION_TG_URL", "")
    monkeypatch.setattr("pension_metrics.WAITLIST_JSON", tmp_path / "waitlist.json")
    monkeypatch.setattr("pension_metrics.WEEKLY_JSON", tmp_path / "weekly.json")
    monkeypatch.setattr("pension_metrics.BASE_DIR", tmp_path)

    from importlib import reload

    import web_app

    reload(web_app)
    client = TestClient(web_app.app)
    r = client.get("/about")
    assert r.status_code == 200
    assert 'href="https://t.me/pensiya_nikogda"' in r.text
