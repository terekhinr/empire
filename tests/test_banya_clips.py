"""Нормализация клипов бань (без БД)."""

from __future__ import annotations

from main import normalize_clip_list


def test_clip_embed_strips_javascript_scheme():
    out = normalize_clip_list([{"provider": "x", "embed_url": "javascript:alert(1)"}])
    assert len(out) == 1
    assert out[0]["embed_url"] == ""


def test_clip_embed_keeps_https():
    out = normalize_clip_list([{"embed_url": "https://example.com/embed/1"}])
    assert out[0]["embed_url"] == "https://example.com/embed/1"


def test_clip_embed_root_path_ok():
    out = normalize_clip_list([{"embed_url": "/clips/a.mp4"}])
    assert out[0]["embed_url"] == "/clips/a.mp4"


def test_clip_embed_protocol_relative_stripped():
    out = normalize_clip_list([{"embed_url": "//evil.example/x"}])
    assert out[0]["embed_url"] == ""
