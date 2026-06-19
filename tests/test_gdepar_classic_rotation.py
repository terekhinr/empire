"""Ротация классики gdepar: cooldown между повторами id."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import gdepar_content as gc


def test_classic_cooldown_excludes_recent_ids(tmp_path, monkeypatch):
    classic_path = tmp_path / "classic.json"
    history_path = tmp_path / "used.json"
    entries = [{"id": f"e{i}", "quote": f"q{i}", "author": "A", "work": "W", "text": "t"} for i in range(5)]
    classic_path.write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")

    recent = (datetime.utcnow() - timedelta(days=3)).isoformat()
    history_path.write_text(
        json.dumps({"ids": ["e0"], "last_by_id": {"e0": recent}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(gc, "_CLASSIC_PATH", classic_path)
    monkeypatch.setattr(gc, "_CLASSIC_HISTORY_PATH", history_path)

    picked_ids = set()
    for _ in range(8):
        e = gc.pick_classic_banya_entry()
        assert e
        picked_ids.add(e["id"])

    assert "e0" not in picked_ids or len(picked_ids) > 1
