"""Фрагменты ПСС для вечернего слота Ленин — без обрезков OCR."""

from __future__ import annotations

import lenin_content as lc


BROKEN_SAMPLE = (
    "оветской электрификации необходимыми мате¬ риалами, оборудованием, "
    "продовольствием. Одной из наиболее сложных задач в первый год нэпа было "
    "налаживание нормальных экономических связей, товарообмена между "
    "промышленностью и сельским хозяй-"
)

GOOD_SAMPLE = (
    "Одной из наиболее сложных задач в первый год нэпа было налаживание "
    "нормальных экономических связей, товарообмена между промышленностью "
    "и сельским хозяйством. Без этого невозможно было двигаться вперёд."
)


def test_repair_pss_ocr_fixes_soft_hyphen_and_splits():
    out = lc._repair_pss_ocr("мате¬ риалами, хозяй-\nство")
    assert "материалами" in out
    assert "хозяй-" not in out
    assert "хозяйство" in out


def test_broken_chunk_rejected_or_trimmed():
    out = lc._clean_pss_excerpt(BROKEN_SAMPLE)
    assert not out or "оветской" not in out.lower()
    assert not out or "хозяй-" not in out


def test_good_chunk_kept():
    out = lc._clean_pss_excerpt(GOOD_SAMPLE)
    assert out
    assert out.startswith("Одной")
    assert out.endswith(".")
    assert "хозяйством" in out


def test_chunk_quality_prefers_complete_text():
    assert lc._pss_chunk_quality(GOOD_SAMPLE) > lc._pss_chunk_quality(BROKEN_SAMPLE)


PLEKHANOV_TABLE_SAMPLE = (
    "3 ЗАМЕЧАНИЯ НА ПЕРВЫЙ ПРОЕКТ ПРОГРАММЫ ПЛЕХАНОВА ТЕКСТ ПЛЕХАНОВА ЗАМЕЧАНИЯ ЛЕНИНА "
    "Страница 1 . JVe 1 — Капитализм не «особенность» современного общества, а его экономический "
    "строй , уклад и т. № 2 — Средства производства принадлежат не только капиталистам. "
    "Главную экономическую особенность современного общества составляет господство в нем "
    "капиталистических производственных отношений, т. принадлежность средств производства."
)


def test_plekhanov_table_chunk_rejected():
    assert not lc._clean_pss_excerpt(PLEKHANOV_TABLE_SAMPLE)
    assert not lc._is_pss_publishable(PLEKHANOV_TABLE_SAMPLE)
    assert "apparatus" in lc._pss_spell_issues(PLEKHANOV_TABLE_SAMPLE)


def test_build_pss_post_escapes_no_broken_blockquote():
    topic, body = lc.build_pss_excerpt_post()
    assert "[ПСС · фрагмент]" in topic
    if "<blockquote>" in body:
        inner = body.split("<blockquote>")[1].split("</blockquote>")[0]
        assert "¬" not in inner
        assert "JVe" not in inner
        assert "ЗАМЕЧАНИЯ НА ПЕРВЫЙ ПРОЕКТ" not in inner
        assert not inner.strip().endswith("-")
        assert inner.strip()[0].isupper() or inner.strip().startswith("«")
        assert not lc._pss_spell_issues(inner)
