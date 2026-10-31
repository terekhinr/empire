"""Тесты варианта A: Obsidian → очередь → dispatch по времени."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import obsidian_content as oc

MSK = ZoneInfo("Europe/Moscow")


def test_parse_scheduled_formats():
    dt = oc.parse_scheduled("2026-06-01 11:00")
    assert dt is not None
    assert dt.hour == 11
    assert dt.month == 6


def test_entries_due_skips_draft_and_dispatched(tmp_path, monkeypatch):
    queue = tmp_path / "queue.json"
    state = tmp_path / "state.json"
    monkeypatch.setattr(oc, "QUEUE_PATH", queue)
    monkeypatch.setattr(oc, "STATE_PATH", state)

    past = (datetime.now(MSK) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    queue.write_text(
        json.dumps(
            [
                {"id": "a", "persona": "pension", "title": "T", "body_markdown": "x", "scheduled": past, "status": "ready"},
                {"id": "b", "persona": "pension", "title": "D", "body_markdown": "x", "scheduled": past, "status": "draft"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    state.write_text(json.dumps({"dispatched_ids": ["a"]}), encoding="utf-8")

    # «a» уже dispatched; «b» — draft
    due = oc.entries_due()
    assert len(due) == 0

    state.write_text(json.dumps({"dispatched_ids": []}), encoding="utf-8")
    due2 = oc.entries_due()
    assert len(due2) == 1
    assert due2[0]["id"] == "a"


def test_obsidian_hashtags_not_title_mash():
    os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")
    from main import finalize_public_post

    entry = {
        "persona": "pension",
        "title": '"Можно ли покупать на новостях?"',
        "body_markdown": "Текст.",
    }
    core = "📌 <b>Заголовок</b>\n\nТекст."
    out = finalize_public_post(core, "pension", "Obsidian", False)
    assert "#obsidian" in out.lower()
    assert "[obsidian]" not in out.lower()
    assert "можнолипокупать" not in out.lower().replace(" ", "")


def test_build_post_html_pension_pin():
    def fix(t):
        return t.replace("**", "")

    def fin(text, p_key, rubric, is_video):
        return text + "\n\n#tag"

    entry = {"persona": "pension", "title": "Заголовок", "body_markdown": "Тело поста."}
    html_out = oc.build_post_html(entry, fix_html_fn=fix, finalize_fn=fin)
    assert "📌" in html_out
    assert "Заголовок" in html_out
    assert "Тело поста" in html_out


def test_build_post_html_garden_leaf_without_obsidian_rubric():
    seen = {}

    def fix(t):
        return t

    def fin(text, p_key, rubric, is_video):
        seen["rubric"] = rubric
        seen["persona"] = p_key
        return text

    entry = {"persona": "garden", "title": "Морковь под зиму", "body_markdown": "Текст."}
    html_out = oc.build_post_html(entry, fix_html_fn=fix, finalize_fn=fin)
    assert html_out.startswith("🌿")
    assert "📌" not in html_out
    assert seen["rubric"] is None
    assert seen["persona"] == "garden"
    assert oc.entry_skips_image({"skip_image": "true"})
    assert not oc.entry_skips_image({})
