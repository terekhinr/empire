"""Тесты донат-бота Ленин и sales.db donations."""

from pathlib import Path

from donate_links import DONATE_CAMPAIGN, alien_campaign_message, donate_deep_link, parse_start_param
from sales_db import donation_stats, init_sales_db, load_donate_campaigns, record_donation


def test_parse_start_lenin_only():
    assert parse_start_param(None) == ("lenin", None)
    assert parse_start_param("donate_lenin") == ("lenin", None)
    assert parse_start_param("donate_lenin_weekly") == ("lenin", "weekly")
    assert parse_start_param("donate_gdepar")[0] == "gdepar"


def test_alien_campaign_hint():
    assert alien_campaign_message("gdepar") is not None
    assert alien_campaign_message("lenin") is None


def test_donate_campaigns_json_lenin_only():
    camps = load_donate_campaigns()
    assert list(camps.keys()) == ["lenin"]


def test_record_donation(tmp_path):
    db = tmp_path / "sales.db"
    init_sales_db(db)
    rid = record_donation(
        tg_user_id=1,
        username="u",
        campaign_code="lenin",
        amount_stars=100,
        amount_rub=180.0,
        currency="XTR",
        payment_method="telegram_stars",
        path=db,
    )
    assert rid >= 1
    s = donation_stats(campaign_code="lenin", days=30, path=db)
    assert s["count"] == 1


def test_deep_link_lenin_only(monkeypatch):
    monkeypatch.setenv("EMPIRE_DONATE_BOT_USERNAME", "lenin_bot")
    assert donate_deep_link("lenin") == "https://t.me/lenin_bot?start=donate_lenin"
    assert donate_deep_link("gdepar") is None
