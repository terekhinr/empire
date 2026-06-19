"""Tests for voice transcript routing into Obsidian vault paths."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from voice_route import (  # noqa: E402
    audio_wikilink,
    classify,
    load_config,
    strip_routing_prefix,
    write_voice_note,
)


@pytest.fixture
def cfg():
    return load_config()


def test_classify_book_one(cfg):
    route = classify("rec.m4a", "Книга один. Глава про подушку безопасности.", cfg)
    assert route.id == "book-neverretire"
    assert route.book == "neverretire"


def test_classify_book_two(cfg):
    route = classify("x.m4a", "Трупик майора. Сцена в кабинете.", cfg)
    assert route.id == "book-trupik"
    assert route.book == "trupik-maiora"


def test_classify_pension_post(cfg):
    route = classify("a.m4a", "Пенсия пост. Тезис про индексные фонды.", cfg)
    assert route.id == "pension-post"
    assert route.vault_path == "Empire/pension/inbox"


def test_classify_article(cfg):
    route = classify("a.m4a", "Статья два. Добавить таблицу FIRE.", cfg)
    assert route.id == "pension-article"


def test_classify_filename(cfg):
    route = classify("book2-scene.m4a", "Продолжение без префикса.", cfg)
    assert route.id == "book-trupik"


def test_classify_default(cfg):
    route = classify("note.m4a", "Просто мысль без ключевых слов.", cfg)
    assert route.id == "inbox"
    assert route.vault_path == "Входящие"


def test_strip_prefix(cfg):
    raw = "Пенсия пост. Тут основной текст."
    assert "основной текст" in strip_routing_prefix(raw, cfg)
    assert "Пенсия пост" not in strip_routing_prefix(raw, cfg)


def test_audio_wikilink_from_empire_inbox():
    link = audio_wikilink(
        "Empire/pension/inbox",
        "rec.m4a",
        "Life/voice/transcribed",
    )
    assert link == "[[../../../Life/voice/transcribed/rec.m4a]]"


def test_write_note(tmp_path, cfg):
    route = classify("a.m4a", "Книга один. Текст.", cfg)
    note = write_voice_note(
        tmp_path,
        route=route,
        audio_name="a.m4a",
        text="Книга один. Текст.",
        stamp=datetime(2026, 6, 3, 12, 0),
        audio_vault_path="Life/voice/transcribed",
    )
    body = note.read_text(encoding="utf-8")
    assert "route: book-neverretire" in body
    assert "book: neverretire" in body
    assert "Текст." in body
    assert "Книга один." not in body or "Текст." in body
