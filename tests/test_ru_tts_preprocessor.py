"""Unit tests: TextPreprocessor + WhisperValidator CER (без загрузки Whisper)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ru_tts.lexicon import ExceptionLexicon  # noqa: E402
from ru_tts.models import MarkupKind  # noqa: E402
from ru_tts.preprocessor import TextPreprocessor  # noqa: E402
from ru_tts.whisper_validator import WhisperValidator, default_suggest_fix  # noqa: E402


def test_glue_clitics_nbsp():
    pp = TextPreprocessor(use_ssml=False)
    out = pp.glue_clitics("книга со стороны банка и не дорого")
    assert "\xa0" in out
    assert "со\xa0стороны" in out or "со\xa0" in out
    assert "не\xa0дорого" in out


def test_homograph_storony():
    pp = TextPreprocessor(use_ssml=True)
    res = pp.process("со стороны банка и обе стороны спора")
    assert "стороны" in res.plain
    # SSML sub для обоих случаев
    assert "<sub" in res.ssml
    assert "<speak>" in res.ssml


def test_phoneme_mnogo_in_ssml():
    pp = TextPreprocessor(use_ssml=True)
    res = pp.process("много акций")
    assert "много" in res.plain
    assert "phoneme" in res.ssml
    assert "mnog" in res.ssml


def test_breaks_on_paragraphs():
    pp = TextPreprocessor(use_ssml=True, paragraph_break_ms=500)
    res = pp.process("Первый абзац.\n\nВторой абзац.")
    assert 'break time="500ms"' in res.ssml


def test_lexicon_apply(tmp_path: Path):
    lex = ExceptionLexicon(tmp_path / "lex.json")
    lex.upsert("дорого", "до́рого", kind=MarkupKind.ALIAS)
    pp = TextPreprocessor(lexicon=lex, use_ssml=True)
    res = pp.process("это слишком дорого")
    assert "дорого" in res.applied_lexicon
    assert "sub" in res.ssml


def test_cer_mnogo_mnovo():
    v = WhisperValidator(ExceptionLexicon(Path("/tmp/ru_tts_lex_test.json")))
    cer = v.char_error_rate("много акций", "мново акций")
    assert cer > 0
    bad = v.align_bad_tokens("много акций", "мново акций")
    assert any(d.ref == "много" and d.hyp == "мново" for d in bad)
    fix = default_suggest_fix("много", "мново")
    assert fix is not None
    assert fix.kind == MarkupKind.PHONEME
