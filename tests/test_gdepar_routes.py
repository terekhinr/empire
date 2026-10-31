"""Маршруты gdepar без обращения к БД (или с мягким skip при отсутствии empire.db)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from gdepar_app import CANONICAL_BASE_URL, app

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_HAVE_DB = os.path.isfile(os.path.join(_ROOT, "empire.db"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_map_trailing_slash_301(client: TestClient) -> None:
    r = client.get("/map/", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers.get("location") == "/map"


def test_banya_without_slug_301(client: TestClient) -> None:
    r = client.get("/banya", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers.get("location") == "/map"


def test_head_home_link_canonical(client: TestClient) -> None:
    r = client.head("/")
    assert r.status_code == 200
    link = r.headers.get("link") or ""
    assert 'rel="canonical"' in link
    assert f"{CANONICAL_BASE_URL}/" in link


def test_head_map_link_canonical(client: TestClient) -> None:
    r = client.head("/map")
    assert r.status_code == 200
    link = r.headers.get("link") or ""
    assert 'rel="canonical"' in link
    assert f"{CANONICAL_BASE_URL}/map" in link


def test_spot_trailing_slash_unknown_404(client: TestClient) -> None:
    r = client.get("/banya/this-slug-should-not-exist-99999/", follow_redirects=False)
    assert r.status_code == 404


def test_robots_txt(client: TestClient) -> None:
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap:" in r.text
    assert "Disallow: /admin/" in r.text
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age=" in cc


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_sitemap_xml_cache_headers(client: TestClient) -> None:
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age=" in cc


def test_api_gdepar_health(client: TestClient) -> None:
    r = client.get("/api/gdepar/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert "assistant" in j
    assert "popup_summary" in j
    assert r.headers.get("strict-transport-security") is None


def test_home_sets_assistant_session_cookie(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "gdepar_asst_sid" in (r.headers.get("set-cookie") or "")


def test_head_api_gdepar_health_200(client: TestClient) -> None:
    r = client.head("/api/gdepar/health")
    assert r.status_code == 200


def test_home_includes_assistant_widget(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "gdepar-assistant-dock" in r.text
    assert 'aria-controls="gdepar-assistant-panel"' in r.text


def test_map_includes_assistant_widget(client: TestClient) -> None:
    r = client.get("/map")
    assert r.status_code == 200
    assert "gdepar-assistant-dock" in r.text


def test_api_unknown_404_json(client: TestClient) -> None:
    r = client.get("/api/this-route-should-not-exist-xyz")
    assert r.status_code == 404
    ctype = r.headers.get("content-type", "")
    assert "application/json" in ctype
    assert "detail" in r.json()


def test_html_404_x_robots_noindex(client: TestClient) -> None:
    r = client.get("/nenahodka-gdepar-test-route-404only")
    assert r.status_code == 404
    tag = (r.headers.get("x-robots-tag") or "").lower()
    assert "noindex" in tag


def test_html_404_includes_assistant_widget(client: TestClient) -> None:
    r = client.get("/nenahodka-gdepar-test-route-404only")
    assert r.status_code == 404
    assert "gdepar-assistant-dock" in r.text


def test_gdepar_home_template_popup_reviews_markup() -> None:
    path = os.path.join(_ROOT, "templates", "gdepar.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "banya-popup-reviews-toggle" in text
    assert "banya-popup-summary-btn" in text
    assert "gdepar-popup-reviews-summary-" in text
    assert "aria-controls=\"gdepar-popup-reviews-body-" in text


def test_gdepar_map_template_popup_reviews_markup() -> None:
    path = os.path.join(_ROOT, "templates", "gdepar_map.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "banya-popup-reviews-toggle" in text
    assert "banya-popup-summary-btn" in text
    assert 'aria-busy' in text


def test_journal_200(client: TestClient) -> None:
    r = client.get("/journal")
    assert r.status_code == 200
    assert "Журнал" in r.text
    assert f"{CANONICAL_BASE_URL}/journal" in (r.headers.get("link") or "")


def test_studio_login_noindex(client: TestClient) -> None:
    r = client.get("/admin/studio/login", follow_redirects=False)
    assert r.status_code in (200, 303, 307, 308, 503)
    if r.status_code == 200:
        tag = (r.headers.get("x-robots-tag") or "").lower()
        assert "noindex" in tag


def test_studio_head_not_405(client: TestClient) -> None:
    """Chrome/Telegram prefetch шлёт HEAD; 405 — ссылка «не открывается»."""
    for path in ("/admin/studio", "/admin/studio/", "/admin/studio/login"):
        r = client.head(path, follow_redirects=False)
        assert r.status_code in (200, 303, 307, 308, 503), path
        if r.status_code in (303, 307, 308):
            assert r.headers.get("location")


def test_admin_login_x_robots_noindex(client: TestClient) -> None:
    r = client.get("/admin/banya/login", follow_redirects=False)
    assert r.status_code in (200, 303, 307, 308, 503)
    if r.status_code == 200:
        tag = (r.headers.get("x-robots-tag") or "").lower()
        assert "noindex" in tag


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует — интеграционные проверки пропущены")
def test_home_200(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "og:image" in r.text or 'property="og:image"' in r.text
    home_canon = f"{CANONICAL_BASE_URL}/"
    link = r.headers.get("link") or ""
    assert 'rel="canonical"' in link
    assert home_canon in link


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_map_200_link_canonical(client: TestClient) -> None:
    r = client.get("/map")
    assert r.status_code == 200
    expect = f"{CANONICAL_BASE_URL}/map"
    link = r.headers.get("link") or ""
    assert 'rel="canonical"' in link
    assert expect in link


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_spot_trailing_slash_301(client: TestClient) -> None:
    import sqlite3

    con = sqlite3.connect(os.path.join(_ROOT, "empire.db"))
    row = con.execute(
        "SELECT slug FROM banya_spots WHERE status='published' AND slug IS NOT NULL "
        "AND TRIM(slug) != '' LIMIT 1"
    ).fetchone()
    con.close()
    if not row:
        pytest.skip("нет опубликованных бань со slug")
    slug = row[0]
    r = client.get(f"/banya/{slug}/", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers.get("location") == f"/banya/{slug}"


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_spot_page_assistant_and_summary_a11y(client: TestClient) -> None:
    import sqlite3

    con = sqlite3.connect(os.path.join(_ROOT, "empire.db"))
    row = con.execute(
        "SELECT slug FROM banya_spots WHERE status='published' AND slug IS NOT NULL "
        "AND TRIM(slug) != '' LIMIT 1"
    ).fetchone()
    con.close()
    if not row:
        pytest.skip("нет опубликованных бань со slug")
    slug = row[0]
    r = client.get(f"/banya/{slug}")
    if r.status_code != 200:
        pytest.skip("slug из БД не отдал 200")
    html = r.text
    assert "gdepar-assistant-dock" in html
    assert "gdepar-spot-summary-btn" in html
    assert 'aria-controls="gdepar-spot-summary-out"' in html
    assert 'id="gdepar-spot-summary-out"' in html
    assert 'aria-live="polite"' in html


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_spot_conditional_304(client: TestClient) -> None:
    import sqlite3

    con = sqlite3.connect(os.path.join(_ROOT, "empire.db"))
    row = con.execute(
        "SELECT slug FROM banya_spots WHERE status='published' AND slug IS NOT NULL "
        "AND TRIM(slug) != '' LIMIT 1"
    ).fetchone()
    con.close()
    if not row:
        pytest.skip("нет опубликованных бань со slug")
    slug = row[0]
    page_url = f"{CANONICAL_BASE_URL}/banya/{slug}"
    r = client.get(f"/banya/{slug}")
    if r.status_code != 200:
        pytest.skip("slug из БД не отдал 200")
    link = r.headers.get("link") or ""
    assert 'rel="canonical"' in link
    assert page_url in link
    rh = client.head(f"/banya/{slug}")
    assert rh.status_code == 200
    assert page_url in (rh.headers.get("link") or "")
    lm = r.headers.get("last-modified")
    if not lm:
        pytest.skip("нет Last-Modified (нет updated_at)")
    r2 = client.get(f"/banya/{slug}", headers={"If-Modified-Since": lm})
    assert r2.status_code == 304
    assert not r2.content
    link304 = r2.headers.get("link") or ""
    assert 'rel="canonical"' in link304
    assert page_url in link304
    r3 = client.head(f"/banya/{slug}", headers={"If-Modified-Since": lm})
    assert r3.status_code == 304
