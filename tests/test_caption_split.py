"""Разбиение длинного caption для Telegram photo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import _admin_caption_for_photo


def test_short_text_unchanged():
    text = "Короткий пост."
    cap, cont = _admin_caption_for_photo(text, max_len=1024)
    assert cap == text
    assert cont is None


def test_long_text_splits_without_duplication():
    p1 = "А" * 400 + "\n\n" + "Б" * 400 + "\n\n"
    p2 = "В" * 500
    text = p1 + p2
    cap, cont = _admin_caption_for_photo(text, max_len=1024)
    assert len(cap) <= 1024
    assert cont is not None
    assert "↓ продолжение ниже" in cap
    assert "↑ продолжение" in cont
    assert p2.strip() in cont
    assert cap.replace("↓ продолжение ниже", "").strip() not in cont.replace("↑ продолжение", "")


def test_stern_like_post():
    text = (
        "<b>Грудной отдел</b>\n\n"
        "Первый абзац про стол и осанку. " * 30
        + "\n\n"
        + "Второй абзац про телефон. " * 30
        + "\n\n"
        + "Третий абзац про сумку и Цацулина. " * 20
    )
    cap, cont = _admin_caption_for_photo(text, max_len=1024)
    assert cont is not None
    plain_cap = cap.split("<i>")[0]
    assert text[len(plain_cap.rstrip()) :].strip()[:40] in cont
