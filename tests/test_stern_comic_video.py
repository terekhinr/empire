"""Штерн: еженедельное комик-видео."""

from pathlib import Path

import pytest

import stern_comic_video

_MATRIX = Path(__file__).resolve().parents[1] / "data" / "stern_comic_video_matrix.json"


def test_matrix_file_exists():
    assert _MATRIX.is_file()
    data = stern_comic_video.load_matrix()
    assert len(data.get("entries") or []) >= 5


def test_comic_slot_fallback_without_ready_clips():
    import asyncio

    topic, body, video, seed = asyncio.run(stern_comic_video.build_comic_slot())
    assert "[Комик техника]" in topic
    assert seed is None or video is None


def test_entry_id_from_topic():
    assert (
        stern_comic_video.entry_id_from_topic(
            "[Комик техника] Мах (id=comic_002_swing)"
        )
        == "comic_002_swing"
    )
