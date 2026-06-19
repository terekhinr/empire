from pension_metrics import append_waitlist_email, load_weekly_metrics, save_weekly_row


def test_waitlist_and_weekly(tmp_path, monkeypatch):
    wl = tmp_path / "wl.json"
    wk = tmp_path / "wk.json"
    monkeypatch.setattr("pension_metrics.WAITLIST_JSON", wl)
    monkeypatch.setattr("pension_metrics.WEEKLY_JSON", wk)
    adb = tmp_path / "a.db"
    monkeypatch.setattr("analytics_db.ANALYTICS_DB_PATH", adb)

    assert append_waitlist_email("a@b.c", source="test")
    assert append_waitlist_email("a@b.c") is True
    save_weekly_row({"week": "2026-05-19", "site_sessions": 100, "orders": 2})
    rows = load_weekly_metrics()
    assert len(rows) == 1
    assert rows[0]["site_sessions"] == 100
