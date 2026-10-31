"""PDF audiobook TTS provider selection and PDF cleanup."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_bot():
    path = ROOT / "bots/stepanich/pdf_audio_bot.py"
    name = "pdf_audio_bot_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_resolve_tts_provider_prefers_yandex(monkeypatch):
    mod = _load_bot()
    monkeypatch.setenv("PDF_AUDIO_TTS_PROVIDER", "auto")
    monkeypatch.setenv("YANDEX_API_KEY", "test-key")
    assert mod.resolve_tts_provider() == "yandex"


def test_resolve_tts_provider_silero_without_yandex(monkeypatch):
    mod = _load_bot()
    monkeypatch.setenv("PDF_AUDIO_TTS_PROVIDER", "auto")
    monkeypatch.delenv("YANDEX_API_KEY", raising=False)
    monkeypatch.delenv("SPEECHKIT_API_KEY", raising=False)
    # load_dotenv inside resolve may re-read .env — stub yandex_available
    monkeypatch.setattr(mod, "yandex_available", lambda: False)
    assert mod.resolve_tts_provider() == "silero"


def test_resolve_tts_provider_explicit_edge(monkeypatch):
    mod = _load_bot()
    monkeypatch.setenv("PDF_AUDIO_TTS_PROVIDER", "edge")
    monkeypatch.setenv("YANDEX_API_KEY", "test-key")
    assert mod.resolve_tts_provider() == "edge"


def test_pdf_noise_line():
    mod = _load_bot()
    assert mod._is_pdf_noise_line("42")
    assert mod._is_pdf_noise_line("— 12 —")
    assert mod._is_pdf_noise_line("28 авг 01:25")
    assert mod._is_pdf_noise_line("01:25")
    assert not mod._is_pdf_noise_line("Глава первая")


def test_infer_title_skips_telegram_date():
    mod = _load_bot()
    lines = [
        "28 авг 01:25",
        "Норникель, Северсталь и ММК — у наших сталеваров проблемы.",
        "Дальше текст статьи.",
    ]
    title, body = mod._infer_title_from_lines(lines, Path("2_5226514727198300573.pdf"))
    assert "авг" not in title.lower()
    assert "Норникель" in title
    assert body and "Дальше" in body[0]


def test_drop_repeated_headers():
    mod = _load_bot()
    lines = ["Колонтитул"] * 20 + ["Нормальный абзац текста книги."]
    out = mod._drop_repeated_pdf_lines(lines)
    assert "Колонтитул" not in out
    assert "Нормальный абзац" in out[0]
