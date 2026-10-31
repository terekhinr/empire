"""Классификатор offtopic бань (adult / агрегатор / отзывы)."""

from tools.banya_hide_offtopic import score_review_text, title_reasons


def test_title_vip_sauna():
    assert "title_adult_leisure" in title_reasons("VIP-сауна", None)


def test_title_klub_saun():
    assert "title_adult_leisure" in title_reasons("Клуб саун Остров", "")


def test_title_normal_sauna_not_flagged():
    assert title_reasons("Сауна на Белградской", None) == []
    assert title_reasons("Финская сауна", "хороший пар") == []


def test_title_aggregator():
    assert "title_aggregator" in title_reasons("Сауны Питера", None)


def test_review_friends_devochki_not_flagged():
    text = "Ходили с девочками на день рождения, парная супер"
    score, tags = score_review_text(text)
    assert score == 0
    assert tags == []


def test_review_adult_flagged():
    text = "Предоставляют девушек по часу, интим услуги"
    score, tags = score_review_text(text)
    assert score >= 4
    assert tags
