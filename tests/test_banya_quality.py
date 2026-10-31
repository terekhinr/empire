"""Тесты quality gate бань (R7)."""

from __future__ import annotations

from datetime import datetime, timedelta

from tools.banya_quality import (
    parse_review_date,
    review_is_fresh,
    title_is_sauna_only,
    traffic_ok,
)


def test_parse_relative_dates():
    now = datetime(2026, 9, 16, 12, 0, 0)
    assert parse_review_date("сегодня", now=now) == datetime(2026, 9, 16)
    assert parse_review_date("вчера", now=now) == datetime(2026, 9, 15)
    assert parse_review_date("3 дня назад", now=now) == datetime(2026, 9, 13)
    assert parse_review_date("2 недели назад", now=now) == datetime(2026, 9, 2)


def test_parse_absolute_ru():
    assert parse_review_date("12 января 2025") == datetime(2025, 1, 12)
    assert parse_review_date("май 2024") == datetime(2024, 5, 1)
    assert parse_review_date("2025-03-01") == datetime(2025, 3, 1)


def test_review_freshness():
    now = datetime(2026, 9, 16)
    assert review_is_fresh(now - timedelta(days=30), now=now) is True
    assert review_is_fresh(now - timedelta(days=600), now=now) is False
    assert review_is_fresh(None, now=now) is False


def test_traffic_and_sauna_title(monkeypatch):
    monkeypatch.setenv("BANYA_MIN_REVIEWS", "50")
    monkeypatch.setenv("BANYA_MIN_RATING", "4.0")
    assert traffic_ok(100, "4.5") is True
    assert traffic_ok(40, "5.0") is False
    assert traffic_ok(50, "3.2") is False
    assert traffic_ok(0, "5.0") is False
    assert traffic_ok(0, "5.0", unknown_ok=True) is True
    assert traffic_ok(None, None, unknown_ok=True) is True
    assert title_is_sauna_only("Сауна Эдем") is True
    assert title_is_sauna_only("Сандуновские бани") is False


def test_review_age_defaults(monkeypatch):
    monkeypatch.delenv("BANYA_REVIEW_MAX_AGE_DAYS", raising=False)
    from tools import banya_quality as bq
    now = datetime(2026, 9, 16)
    # дефолт 365 дней
    assert bq.review_is_fresh(now - timedelta(days=300), now=now) is True
    assert bq.review_is_fresh(now - timedelta(days=400), now=now) is False
