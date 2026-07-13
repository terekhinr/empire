"""Тесты content_audit."""

from content_audit import audit_text, _is_curated_topic, _is_llm_slot_topic


def test_stern_cliche_detected():
    text = "🛎️ История гирь\n\nГиря — не просто железный шар с ручкой."
    issues = audit_text(text, "stern", topic_raw="[История гирь] test")
    assert any("клише" in i for i in issues)


def test_gdepar_curated_marker():
    assert _is_curated_topic("[Дуэт] Париться молча (id=duo_silence)")
    assert not _is_curated_topic("Свободная тема")


def test_garden_llm_slot_flag():
    assert _is_llm_slot_topic("[План на день] Сводка погоды")
    issues = audit_text("Погода в ЦФО норм", "garden", topic_raw="[План на день] x")
    assert any("LLM-слот" in i for i in issues)
