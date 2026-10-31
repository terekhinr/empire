"""Дедуп отзывов бань: стабильный id и выбор канонической строки."""

from tools.banya_review_dedupe import pick_keeper, stable_review_source_id


def test_stable_id_same_text():
    a = stable_review_source_id("  Отличная баня, жарко.  ")
    b = stable_review_source_id("Отличная баня, жарко.")
    assert a == b
    assert len(a) == 16


def test_stable_id_differs_for_other_text():
    assert stable_review_source_id("раз") != stable_review_source_id("два")


def test_pick_keeper_prefers_approved_then_older():
    rows = [
        {"id": 30, "status": "pending"},
        {"id": 10, "status": "approved"},
        {"id": 20, "status": "approved"},
        {"id": 5, "status": "hidden"},
    ]
    keep = pick_keeper(rows)
    assert keep["id"] == 10
