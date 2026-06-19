"""ТЗ §3–§4: прозрачность ответов помощника и сводки отзывов."""

from __future__ import annotations

import asyncio
import logging
import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from gdepar_app import (
    _ASSISTANT_RL_BUCKETS,
    _GDEPAR_TRANSPARENCY_NOTE,
    _assistant_cache,
    _assistant_cache_key,
    _assistant_llm_rollout_for_client_today,
    _assistant_llm_user_prompt_max_chars,
    _assistant_load_catalog_for_prompt,
    _assistant_message_likely_spam,
    _assistant_review_line_for_llm,
    _assistant_stub_recommendations,
    _build_reviews_block_payload,
    _clean_review_snippet_text,
    _popup_summary_llm_selected_for_spot_today,
    _reviews_summary_html,
    _reviews_summary_parts_heuristic,
    app,
)


def test_reviews_block_payload_has_transparency_note() -> None:
    p = _build_reviews_block_payload([], 5)
    assert p.get("transparency_note") == _GDEPAR_TRANSPARENCY_NOTE


def test_clean_review_snippet_strips_yandex_boilerplate() -> None:
    raw = (
        "Отзыв слишком длинный — на сайте показана часть. "
        "Оригинал полностью: Яндекс.Карты. "
        "Отличная парная, тёплая атмосфера."
    )
    assert "Яндекс" not in _clean_review_snippet_text(raw)
    assert "Отличная парная" in _clean_review_snippet_text(raw)


def test_reviews_summary_html_structured_not_wall() -> None:
    from datetime import datetime, timezone

    reviews = [
        SimpleNamespace(
            id=1,
            text="Отличная баня, просторная парная и внимательный персонал " * 3,
            author="Иван П.",
            rating=5,
            published_at=datetime(2026, 5, 21, tzinfo=timezone.utc),
            fetched_at=None,
            source="yandex",
        ),
        SimpleNamespace(
            id=2,
            text="Уютно, чисто, хороший пар.",
            author="Мария",
            rating=5,
            published_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
            fetched_at=None,
            source="yandex",
        ),
    ]
    parts = _reviews_summary_parts_heuristic(reviews)
    html = _reviews_summary_html(parts)
    assert "gdepar-summary-card" in html
    assert "gdepar-summary-quotes" in html
    assert "Основные ноты из текстов" not in html

    p = _build_reviews_block_payload(reviews, 2)
    assert p.get("summary_html")
    assert "gdepar-summary-quotes" in p["summary_html"]
    assert isinstance(p.get("summary_highlights"), list)
    assert len(p.get("summary_highlights") or []) >= 1


def test_assistant_toxic_blocked_when_regex_matches(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_TOXIC_REGEX", r"XXX_TOXIC_TEST_TOKEN_XXX")
    c = TestClient(app)
    r = c.post(
        "/api/gdepar/assistant",
        json={"message": "ищу баню XXX_TOXIC_TEST_TOKEN_XXX в городе"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("toxic_blocked") is True
    assert j.get("stub") is True
    assert isinstance(j.get("llm_rollout"), bool)


def test_assistant_toxic_invalid_regex_does_not_block(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_TOXIC_REGEX", "(")
    c = TestClient(app)
    r = c.post("/api/gdepar/assistant", json={"message": "нужна баня в Химках"})
    assert r.status_code == 200
    assert r.json().get("toxic_blocked") is not True


def test_assistant_llm_user_prompt_max_chars_clamped(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_PROMPT_MAX_CHARS", "999999")
    assert _assistant_llm_user_prompt_max_chars() == 100_000
    monkeypatch.setenv("GDEPAR_ASSISTANT_PROMPT_MAX_CHARS", "100")
    assert _assistant_llm_user_prompt_max_chars() == 8000


def test_assistant_llm_rollout_stable_for_same_client(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key")
    monkeypatch.setenv("GDEPAR_ASSISTANT_LLM", "1")
    monkeypatch.setenv("GDEPAR_ASSISTANT_LLM_PCT", "50")
    fp = "test_client_fp_abc"
    a = _assistant_llm_rollout_for_client_today(fp)
    b = _assistant_llm_rollout_for_client_today(fp)
    assert a is b


def test_assistant_llm_rollout_pct_zero(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key")
    monkeypatch.setenv("GDEPAR_ASSISTANT_LLM", "1")
    monkeypatch.setenv("GDEPAR_ASSISTANT_LLM_PCT", "0")
    assert _assistant_llm_rollout_for_client_today("any_fp") is False


def test_assistant_stub_recommendations_min_three_when_catalog_allows() -> None:
    pool = asyncio.run(_assistant_stub_recommendations(None, "all", None, max_picks=20, fetch_cap=48))
    if len(pool) >= 3:
        capped = asyncio.run(
            _assistant_stub_recommendations(None, "all", None, max_picks=7, min_picks=3, fetch_cap=48)
        )
        assert len(capped) >= 3
        assert len(capped) <= 7


def test_assistant_stub_recommendations_shape() -> None:
    recs = asyncio.run(_assistant_stub_recommendations(None, "all", None, max_picks=5))
    assert isinstance(recs, list)
    for item in recs:
        assert set(item.keys()) >= {"spot_id", "slug", "title", "reason"}
        assert "без ИИ" in (item.get("reason") or "")


def test_assistant_stream_empty_done_event() -> None:
    c = TestClient(app)
    r = c.post("/api/gdepar/assistant/stream", json={"message": "   "})
    assert r.status_code == 200
    assert "text/event-stream" in (r.headers.get("content-type") or "").lower()
    assert "event: done" in r.text
    assert '"empty": true' in r.text or '"empty":true' in r.text


def test_assistant_stream_stub_emits_delta() -> None:
    _ASSISTANT_RL_BUCKETS.clear()
    _assistant_cache.clear()
    c = TestClient(app)
    r = c.post("/api/gdepar/assistant/stream", json={"message": "ищу дровяную баню"})
    assert r.status_code == 200
    assert "event: done" in r.text
    assert "event: delta" in r.text
    assert "disclaimer" in r.text


def test_assistant_empty_request_no_stub_log(caplog) -> None:
    _ASSISTANT_RL_BUCKETS.clear()
    caplog.set_level(logging.INFO, logger="gdepar.assistant")
    c = TestClient(app)
    r = c.post("/api/gdepar/assistant", json={"message": "   "})
    assert r.status_code == 200
    j = r.json()
    assert j.get("empty") is True
    assert not any("stub query" in rec.getMessage() for rec in caplog.records)


def test_assistant_rate_limit_429(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_RL_PER_MIN", "1")
    monkeypatch.setenv("GDEPAR_ASSISTANT_RL_DISABLE", "0")
    _ASSISTANT_RL_BUCKETS.clear()
    _assistant_cache.clear()
    c = TestClient(app)
    r1 = c.post("/api/gdepar/assistant", json={"message": "первый запрос rl"})
    assert r1.status_code == 200
    r2 = c.post("/api/gdepar/assistant", json={"message": "второй запрос rl"})
    assert r2.status_code == 429
    j2 = r2.json()
    assert j2.get("rate_limited") is True
    assert j2.get("disclaimer") == _GDEPAR_TRANSPARENCY_NOTE


def test_assistant_stub_reply_seen_spot_ids_truncated_at_24() -> None:
    seen = list(range(1, 30))
    c = TestClient(app)
    r = c.post(
        "/api/gdepar/assistant",
        json={"message": "нужна баня", "seen_spot_ids": seen},
    )
    assert r.status_code == 200
    reply = r.json().get("reply") or ""
    assert "уже смотрели" in reply
    assert "…" in reply
    assert ",25" not in reply


def test_assistant_spam_not_cached(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_CACHE_SECONDS", "3600")
    _assistant_cache.clear()
    c = TestClient(app)
    msg = "xxxxxxxxxxxxxxxx"
    r1 = c.post("/api/gdepar/assistant", json={"message": msg})
    r2 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r1.status_code == 200
    assert r2.status_code == 200
    j1 = r1.json()
    j2 = r2.json()
    assert j1.get("spam_blocked") is True
    assert j2.get("spam_blocked") is True
    assert j1.get("cached") is not True
    assert j2.get("cached") is not True


def test_assistant_toxic_not_cached(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_CACHE_SECONDS", "3600")
    monkeypatch.setenv("GDEPAR_ASSISTANT_TOXIC_REGEX", r"XXX_TOXIC_CACHE_XXX")
    _assistant_cache.clear()
    c = TestClient(app)
    msg = "баня XXX_TOXIC_CACHE_XXX"
    r1 = c.post("/api/gdepar/assistant", json={"message": msg})
    r2 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json().get("toxic_blocked") is True
    assert r2.json().get("toxic_blocked") is True
    assert r1.json().get("cached") is not True
    assert r2.json().get("cached") is not True


def test_assistant_cache_hit_bypasses_rate_limit(monkeypatch) -> None:
    """ТЗ §3 v1: попадание в кэш не списывает RL."""
    monkeypatch.setenv("GDEPAR_ASSISTANT_RL_PER_MIN", "1")
    monkeypatch.setenv("GDEPAR_ASSISTANT_RL_DISABLE", "0")
    monkeypatch.setenv("GDEPAR_ASSISTANT_CACHE_SECONDS", "3600")
    _ASSISTANT_RL_BUCKETS.clear()
    _assistant_cache.clear()
    c = TestClient(app)
    msg = f"cache rl bypass {uuid.uuid4().hex}"
    r1 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r1.status_code == 200
    assert r1.json().get("cached") is not True

    r2 = c.post("/api/gdepar/assistant", json={"message": "другой запрос после лимита"})
    assert r2.status_code == 429
    assert r2.json().get("rate_limited") is True

    r3 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r3.status_code == 200
    assert r3.json().get("cached") is True


def test_assistant_responses_include_disclaimer() -> None:
    c = TestClient(app)
    r0 = c.post("/api/gdepar/assistant", json={"message": "   "})
    assert r0.status_code == 200
    j0 = r0.json()
    assert j0.get("disclaimer") == _GDEPAR_TRANSPARENCY_NOTE
    assert j0.get("llm_rollout") is False

    r1 = c.post("/api/gdepar/assistant", json={"message": "нужна баня"})
    assert r1.status_code == 200
    j = r1.json()
    assert j.get("disclaimer") == _GDEPAR_TRANSPARENCY_NOTE
    assert "llm_rollout" in j
    assert isinstance(j.get("llm_rollout"), bool)
    assert "без языковой модели" in (j.get("reply") or "")
    recs = j.get("recommendations")
    if recs:
        assert isinstance(recs, list)
        assert all(isinstance(x.get("spot_id"), int) for x in recs)
        assert "Ниже — несколько точек" in (j.get("reply") or "")

    r2 = c.post(
        "/api/gdepar/assistant",
        json={"message": "тест", "city": "Химки", "heat": "wood"},
    )
    assert r2.status_code == 200
    j2 = r2.json()
    reply2 = j2.get("reply") or ""
    assert "Химки" in reply2
    assert "wood" in reply2
    assert isinstance(j2.get("llm_rollout"), bool)


def test_assistant_cache_key_whitespace_normalized() -> None:
    a = _assistant_cache_key("  hello  world  ", None, None, None, llm_mode=False)
    b = _assistant_cache_key("hello world", None, None, None, llm_mode=False)
    assert a == b


def test_assistant_cache_key_llm_mode_separate() -> None:
    a = _assistant_cache_key("x", "map", None, None, llm_mode=False)
    b = _assistant_cache_key("x", "map", None, None, llm_mode=True)
    assert a != b


def test_assistant_cache_key_seen_spot_ids_change_hash() -> None:
    a = _assistant_cache_key("q", None, None, None, llm_mode=False, seen_spot_ids=None)
    b = _assistant_cache_key("q", None, None, None, llm_mode=False, seen_spot_ids=[1, 2])
    assert a != b


def test_reviews_block_include_summary_0_list_only() -> None:
    c = TestClient(app)
    r = c.get("/api/banya/reviews-block/1?limit=3&include_summary=0")
    assert r.status_code == 200
    j = r.json()
    assert j.get("summary") is None
    assert "transparency_note" not in j
    assert "summary_source" not in j
    assert isinstance(j.get("reviews"), list)


def test_reviews_block_include_summary_1_transparency_and_source() -> None:
    c = TestClient(app)
    r = c.get("/api/banya/reviews-block/1?limit=3&include_summary=1")
    assert r.status_code == 200
    j = r.json()
    assert j.get("transparency_note") == _GDEPAR_TRANSPARENCY_NOTE
    assert isinstance(j.get("summary"), str)
    assert j.get("summary_source") in ("heuristic", "llm")
    if j.get("summary"):
        assert isinstance(j.get("summary_html"), str)
        assert "gdepar-summary-card" in (j.get("summary_html") or "")


def test_reviews_block_include_summary_has_summary_source() -> None:
    c = TestClient(app)
    r = c.get("/api/banya/reviews-block/1?limit=3&include_summary=1")
    assert r.status_code == 200
    j = r.json()
    assert j.get("summary_source") in ("heuristic", "llm")


def test_assistant_accepts_seen_spot_ids() -> None:
    c = TestClient(app)
    r = c.post(
        "/api/gdepar/assistant",
        json={"message": "тест seen", "seen_spot_ids": [9, 9, 1, -1, 0, "2"]},
    )
    assert r.status_code == 200
    jr = r.json()
    assert jr.get("disclaimer") == _GDEPAR_TRANSPARENCY_NOTE
    assert isinstance(jr.get("llm_rollout"), bool)


def test_gdepar_assistant_in_seen_spot_ids_max_48_unique() -> None:
    from gdepar_app import GdeparAssistantIn

    long = list(range(1, 80))
    body = GdeparAssistantIn(message="x", seen_spot_ids=long)
    assert body.seen_spot_ids is not None
    assert len(body.seen_spot_ids) == 48
    assert body.seen_spot_ids[0] == 1
    assert body.seen_spot_ids[-1] == 48


def test_assistant_cache_hit_on_second_request(monkeypatch) -> None:
    monkeypatch.setenv("GDEPAR_ASSISTANT_CACHE_SECONDS", "3600")
    _assistant_cache.clear()
    c = TestClient(app)
    msg = f"cache roundtrip {uuid.uuid4().hex}"
    r1 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1.get("disclaimer") == _GDEPAR_TRANSPARENCY_NOTE
    assert j1.get("cached") is not True

    r2 = c.post("/api/gdepar/assistant", json={"message": msg})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2.get("cached") is True
    assert j2.get("reply") == j1.get("reply")


def test_assistant_review_line_for_llm_format() -> None:
    rv = SimpleNamespace(spot_id=12, rating=5, text="  Строка\nдругая  ")
    line = _assistant_review_line_for_llm(rv)
    assert line == "review|12|5|Строка другая"


def test_assistant_review_line_truncates_long_text() -> None:
    tail = "б" * 400
    rv = SimpleNamespace(spot_id=1, rating=None, text="а" + tail)
    line = _assistant_review_line_for_llm(rv)
    assert line.startswith("review|1||")
    assert "…" in line
    assert len(line) < 280


def test_assistant_catalog_bundle_fourth_slot_is_string() -> None:
    lines, ids, slugs, rev = asyncio.run(_assistant_load_catalog_for_prompt(None, "all", 2))
    assert isinstance(lines, list)
    assert isinstance(ids, set)
    assert isinstance(slugs, dict)
    assert isinstance(rev, str)


def test_assistant_message_likely_spam_heuristic() -> None:
    assert _assistant_message_likely_spam("hi") is False
    assert _assistant_message_likely_spam("xxxxxxxxxxxx") is True
    spam_urls = " ".join([f"http://x{i}.test" for i in range(7)])
    assert _assistant_message_likely_spam(spam_urls) is True


def test_assistant_spam_blocked_json() -> None:
    c = TestClient(app)
    r = c.post("/api/gdepar/assistant", json={"message": "xxxxxxxxxxxxxxxx"})
    assert r.status_code == 200
    j = r.json()
    assert j.get("spam_blocked") is True
    assert j.get("stub") is True
    assert isinstance(j.get("llm_rollout"), bool)


def test_popup_summary_llm_selection_stable(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("GDEPAR_POPUP_SUMMARY_LLM", "1")
    monkeypatch.setenv("GDEPAR_POPUP_SUMMARY_LLM_PCT", "50")
    a = _popup_summary_llm_selected_for_spot_today(42)
    b = _popup_summary_llm_selected_for_spot_today(42)
    assert a is b


def test_popup_summary_llm_pct_zero(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("GDEPAR_POPUP_SUMMARY_LLM", "1")
    monkeypatch.setenv("GDEPAR_POPUP_SUMMARY_LLM_PCT", "0")
    assert _popup_summary_llm_selected_for_spot_today(1) is False
