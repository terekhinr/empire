import json
from pathlib import Path

import empire_flags


def test_load_defaults_when_missing(tmp_path, monkeypatch):
    p = tmp_path / "empire_flags.json"
    monkeypatch.setattr(empire_flags, "_FLAGS_PATH", p)
    flags = empire_flags.load_empire_flags()
    assert flags["stop_neurocomment"] is True
    assert flags["stop_publications"] is False


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    p = tmp_path / "empire_flags.json"
    monkeypatch.setattr(empire_flags, "_FLAGS_PATH", p)
    empire_flags.save_empire_flags({"stop_publications": True, "stop_worker": True})
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["stop_publications"] is True
    loaded = empire_flags.load_empire_flags()
    assert loaded["stop_publications"] is True
    assert loaded["stop_worker"] is True
