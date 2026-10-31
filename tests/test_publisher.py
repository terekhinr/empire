"""Тесты Ops Studio: парсер, банк, fallback, notify, tick, HTTP API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates

from publisher.app import configure, router
from publisher.bank import fill_slots_from_bank, new_bank_post, pick_bank_post
from publisher.catalog import seed_slots_from_content_config
from publisher.dispatch import tick
from publisher.media import pick_fallback, resolve_post_image
from publisher.notify import format_event, normalize_bot_settings
from publisher.parse import parse_matrix_text, parse_post_file
from publisher.schedule import assign_next_slots, next_datetime_for_slot
from publisher.store import Store

MSK = ZoneInfo("Europe/Moscow")
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "publisher" / "examples"

LONG_BODY = (
    "Это достаточно длинный текст поста для проверки автопостинга. "
    "Нужно больше восьмидесяти символов, чтобы пройти порог min_body_chars. "
    "Практика, конкретика, без воды."
)


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store.json")


@pytest.fixture(autouse=True)
def _mute_notify(monkeypatch):
    monkeypatch.setattr(
        "publisher.notify.send_admin_text",
        lambda *a, **k: (True, "mocked"),
    )
    monkeypatch.setattr(
        "publisher.dispatch.notify_tick_results",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "publisher.dispatch.maybe_send_digest",
        lambda *a, **k: None,
    )


def test_parse_md_frontmatter():
    p = parse_post_file(
        "x.md",
        "---\nproject: site:gdepar\ntitle: Карта\n---\n\nТекст журнала.\n",
    )
    assert p["project_id"] == "site:gdepar"
    assert p["title"] == "Карта"
    assert "журнала" in p["body"]


def test_parse_md_heading():
    p = parse_post_file("gdepar_utro.md", "# Заголовок\n\nТело поста.\n")
    assert p["title"] == "Заголовок"
    assert p["body"] == "Тело поста."


def test_parse_csv_matrix():
    src = EXAMPLES.joinpath("matrix.csv").read_text(encoding="utf-8")
    rows = parse_matrix_text(src)
    assert len(rows) == 4
    assert rows[0]["weekday"] == 0
    assert rows[0]["slot_time"] == "11:00"
    assert rows[0]["project_id"] == "tg:gdepar"
    assert rows[2]["project_id"] == "site:gdepar"
    assert rows[3]["project_id"] == "tg:stern"


def test_parse_md_table():
    src = """
| день | слот | текст |
| --- | --- | --- |
| Вт | 10:00 | Два подхода |
"""
    rows = parse_matrix_text(src, default_project="tg:stern")
    assert len(rows) == 1
    assert rows[0]["weekday"] == 1
    assert rows[0]["slot_time"] == "10:00"


def test_assign_next_slots(store):
    data = store.load()
    entries = [
        parse_post_file("a.md", f"# Один\n\n{LONG_BODY}", default_project="tg:gdepar"),
        parse_post_file("b.md", f"# Два\n\n{LONG_BODY}", default_project="tg:gdepar"),
    ]
    after = datetime(2026, 8, 31, 8, 0, tzinfo=MSK)
    placed = assign_next_slots(entries, data["slots"], [], after=after, default_project="tg:gdepar")
    assert all(not p.get("error") for p in placed)
    times = [p["scheduled_at"] for p in placed]
    assert times[0] != times[1]


def test_fallback_image_gdepar():
    fb = pick_fallback("gdepar", salt="demo")
    assert fb is not None and fb.is_file()
    path, src = resolve_post_image({"id": "x", "title": "t"}, persona="gdepar", require=True)
    assert path and src == "fallback"


def test_skip_without_image_when_no_archive(store, monkeypatch):
    monkeypatch.delenv("EMPIRE_PUBLISHER_LIVE", raising=False)
    monkeypatch.setattr("publisher.media.list_archive_images", lambda *a, **k: [])
    data = store.load()
    data["mode"] = "test"
    data["bot_settings"] = normalize_bot_settings(
        {"require_image": True, "min_body_chars": 40, "notify_on": []}
    )
    data["posts"] = [
        {
            "id": "post-noimg",
            "project_id": "tg:gdepar",
            "title": "Без фото",
            "body": LONG_BODY,
            "scheduled_at": "2026-08-31 11:00",
            "status": "scheduled",
        }
    ]
    store.save(data)
    result = tick(store, now=datetime(2026, 8, 31, 11, 1, tzinfo=MSK), fill_bank=False)
    assert result["sent"][0]["skipped"] is True
    assert result["sent"][0]["detail"] == "no_image_after_fallback"
    assert store.load()["posts"][0]["status"] == "skipped"


def test_tick_test_mode_with_fallback(store, monkeypatch):
    monkeypatch.delenv("EMPIRE_PUBLISHER_LIVE", raising=False)
    data = store.load()
    data["mode"] = "test"
    data["bot_settings"] = normalize_bot_settings({"min_body_chars": 40})
    data["posts"] = [
        {
            "id": "post-demo",
            "project_id": "tg:gdepar",
            "title": "Тест",
            "body": LONG_BODY,
            "scheduled_at": "2026-08-31 11:00",
            "status": "scheduled",
        }
    ]
    store.save(data)
    result = tick(store, now=datetime(2026, 8, 31, 11, 1, tzinfo=MSK), fill_bank=False)
    assert result["mode"] == "test"
    assert len(result["sent"]) == 1
    assert result["sent"][0]["ok"] is True
    assert result["sent"][0]["detail"] == "test_outbox"
    assert result["sent"][0]["image_source"] in ("ok", "fallback")
    again = store.load()
    assert again["posts"][0]["status"] == "test_sent"


def test_live_blocked_without_env(store, monkeypatch):
    monkeypatch.delenv("EMPIRE_PUBLISHER_LIVE", raising=False)
    data = store.load()
    data["mode"] = "live"
    data["bot_settings"] = normalize_bot_settings({"min_body_chars": 40})
    data["posts"] = [
        {
            "id": "post-live",
            "project_id": "tg:gdepar",
            "title": "Живой",
            "body": LONG_BODY,
            "scheduled_at": "2026-08-31 11:00",
            "status": "scheduled",
        }
    ]
    store.save(data)
    result = tick(store, now=datetime(2026, 8, 31, 12, 0, tzinfo=MSK), fill_bank=False)
    assert result["mode"] == "test"
    assert result["sent"][0]["detail"] == "test_outbox"


def test_bank_rotation_fill(store):
    data = store.load()
    data["slots"] = [
        {
            "id": "slot-x",
            "project_id": "tg:gdepar",
            "weekday": 0,
            "time": "11:00",
            "label": "general",
            "enabled": True,
        }
    ]
    data["posts"] = []
    data["bank_posts"] = [
        new_bank_post(project_id="tg:gdepar", title="A", body=LONG_BODY, category="general"),
        new_bank_post(project_id="tg:gdepar", title="B", body=LONG_BODY + " два", category="general"),
    ]
    created = fill_slots_from_bank(
        data,
        after=datetime(2026, 8, 31, 8, 0, tzinfo=MSK),
        days_ahead=14,
        project_id="tg:gdepar",
    )
    assert len(created) >= 1
    assert created[0]["bank_id"]
    assert data["bank_posts"][0]["times_used"] >= 1 or data["bank_posts"][1]["times_used"] >= 1


def test_pick_bank_respects_cooldown(store):
    bp = new_bank_post(project_id="tg:gdepar", title="C", body=LONG_BODY)
    bp["times_used"] = 1
    bp["last_used_at"] = datetime(2026, 8, 30, tzinfo=MSK).isoformat()
    bp["cooldown_days"] = 21
    bank = [bp]
    assert pick_bank_post(bank, project_id="tg:gdepar", now=datetime(2026, 8, 31, tzinfo=MSK)) is None
    assert pick_bank_post(bank, project_id="tg:gdepar", now=datetime(2026, 9, 25, tzinfo=MSK)) is not None


def test_format_event():
    s = format_event(
        {
            "ok": True,
            "project_id": "tg:gdepar",
            "title": "Привет",
            "scheduled_at": "2026-08-31 15:00",
            "status": "published",
        }
    )
    assert "✓" in s and "gdepar" in s


def test_ai_factory_parse_json():
    from publisher.ai_factory import _parse_json_array

    raw = '```json\n[{"title":"A","body":"' + LONG_BODY + '","category":"x"}]\n```'
    rows = _parse_json_array(raw)
    assert len(rows) == 1 and rows[0]["category"] == "x"


def test_seed_slots_from_real_config():
    import json

    cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
    slots = seed_slots_from_content_config(cfg)
    gdepar = [s for s in slots if s["project_id"] == "tg:gdepar"]
    times = {(s["weekday"], s["time"]) for s in gdepar}
    assert (0, "11:00") in times
    assert (0, "15:00") in times


def test_next_slot_skips_past():
    after = datetime(2026, 8, 31, 16, 0, tzinfo=MSK)
    dt = next_datetime_for_slot(0, "11:00", after=after)
    assert dt is not None
    assert dt.day == 7


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_STUDIO_TOKEN", "studio-test")
    monkeypatch.delenv("EMPIRE_STUDIO_OPEN", raising=False)
    store = Store(tmp_path / "store.json")
    app = FastAPI()
    templates = Jinja2Templates(directory=str(ROOT / "templates"))
    configure(templates, store)
    app.include_router(router)
    c = TestClient(app)
    c.post("/admin/studio/login", data={"token": "studio-test"}, follow_redirects=False)
    return c


def test_studio_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_STUDIO_TOKEN", "secret")
    store = Store(tmp_path / "s.json")
    app = FastAPI()
    configure(Jinja2Templates(directory=str(ROOT / "templates")), store)
    app.include_router(router)
    r = TestClient(app).get("/admin/studio/api/state")
    assert r.status_code == 401


def test_studio_head_redirects_to_login(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_STUDIO_TOKEN", "secret")
    store = Store(tmp_path / "s.json")
    app = FastAPI()
    configure(Jinja2Templates(directory=str(ROOT / "templates")), store)
    app.include_router(router)
    r = TestClient(app).head("/admin/studio", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == "/admin/studio/login"
    r2 = TestClient(app).head("/admin/studio/login", follow_redirects=False)
    assert r2.status_code == 200


def test_studio_upload_and_tick(client):
    files = [
        ("files", ("utro.md", EXAMPLES.joinpath("gdepar_utro.md").read_bytes(), "text/markdown")),
        ("files", ("vecher.md", EXAMPLES.joinpath("gdepar_vecher.md").read_bytes(), "text/markdown")),
    ]
    r = client.post("/admin/studio/api/upload", data={"project_id": "tg:gdepar"}, files=files)
    assert r.status_code == 200, r.text
    created = r.json()["created"]
    assert len([x for x in created if not x.get("error")]) == 2
    post_id = created[0]["id"]
    r2 = client.post("/admin/studio/api/tick", data={"force_id": post_id})
    assert r2.status_code == 200
    sent = r2.json()["sent"]
    assert sent and sent[0]["ok"] and sent[0]["mode"] == "test"


def test_studio_bank_and_fill(client):
    r = client.post(
        "/admin/studio/api/bank",
        data={
            "project_id": "tg:gdepar",
            "title": "Банный совет",
            "body": LONG_BODY,
            "category": "general",
            "cooldown_days": "14",
        },
    )
    assert r.status_code == 200, r.text
    bank_id = r.json()["post"]["id"]
    r2 = client.post(f"/admin/studio/api/bank/{bank_id}/queue")
    assert r2.status_code == 200, r2.text
    assert r2.json()["post"]["status"] == "scheduled"
    st = client.get("/admin/studio/api/state?project=tg:gdepar")
    assert st.json()["bank_count"] >= 1


def test_studio_bot_settings(client):
    r = client.post(
        "/admin/studio/api/bot/settings",
        data={
            "admin_chat_id": "12345",
            "digest": "weekly",
            "notify_published": "1",
            "notify_skipped": "1",
            "notify_failed": "0",
            "require_image": "1",
            "min_body_chars": "50",
        },
    )
    assert r.status_code == 200
    bs = r.json()["bot_settings"]
    assert bs["admin_chat_id"] == "12345"
    assert bs["digest"] == "weekly"
    assert "failed" not in bs["notify_on"]
    assert bs["min_body_chars"] == 50


def test_studio_matrix(client):
    src = EXAMPLES.joinpath("matrix.csv").read_text(encoding="utf-8")
    r = client.post("/admin/studio/api/matrix", data={"text": src, "project_id": ""})
    assert r.status_code == 200, r.text
    created = [x for x in r.json()["created"] if not x.get("error")]
    assert len(created) >= 3


def test_demo_examples_roundtrip(store, monkeypatch):
    from publisher.__main__ import run_demo

    monkeypatch.setattr(
        "publisher.dispatch.notify_tick_results",
        lambda *a, **k: [],
    )
    code = run_demo(store)
    assert code == 0
    data = store.load()
    assert any(p["status"] in ("test_sent", "skipped") for p in data["posts"])
    assert data["outbox"]


def test_split_gemini_pack_and_aliases():
    from publisher.batch_parse import split_gemini_pack

    raw = """
---
id: a1
rubric: степаныч
headline: Грядка
image_prompt_en: soil beds
---
Достаточно длинный текст про грядки и полив для дачи в средней полосе России.

---
id: a2
rubric: kizima_lunar
headline: Луна
---
Достаточно длинный текст про фазы луны и посадку корнеплодов на даче.
"""
    items = split_gemini_pack(raw)
    assert len(items) == 2
    assert items[0]["rubric_id"] == "stepanych"
    assert items[1]["rubric_id"] == "lunar"
    assert items[0]["image_prompt_en"] == "soil beds"


def test_dedupe_similarity():
    from publisher.dedupe import find_duplicate, similarity

    assert similarity("Привет мир", "привет  мир!") > 0.9
    corpus = [
        {
            "title": "Грядка",
            "body": LONG_BODY,
            "text": f"Грядка\n{LONG_BODY}",
            "src": "bank",
        }
    ]
    hit = find_duplicate("Грядка", LONG_BODY, corpus, threshold=0.9)
    assert hit and hit["score"] >= 0.9


def test_import_gemini_skips_dup(store):
    from publisher.bank import import_gemini_pack_to_bank

    pack = f"""---
rubric: stepanych
headline: Один
---
{LONG_BODY}

---
rubric: stepanych
headline: Один
---
{LONG_BODY}
"""
    data = store.load()
    r1 = import_gemini_pack_to_bank(data, pack, project_id="tg:garden")
    assert r1["added"] == 1
    assert r1["skipped_dup"] == 1
    store.save(data)
    r2 = import_gemini_pack_to_bank(store.load(), pack, project_id="tg:garden")
    assert r2["added"] == 0
    assert r2["skipped_dup"] == 2


def test_garden_rubrics_and_stub_generate(store, monkeypatch):
    monkeypatch.setattr(
        "publisher.image_gen.generate_gemini_image",
        lambda *a, **k: None,
    )
    data = store.load()
    assert any(r["id"] == "stepanych" for r in data["rubrics"])
    garden_slots = [s for s in data["slots"] if s.get("project_id") == "tg:garden"]
    assert len(garden_slots) >= 4
    from publisher.media import resolve_rubric_image
    from publisher.rubrics import find_rubric

    rubric = find_rubric(data, project_id="tg:garden", rubric_id="stepanych")
    path, src = resolve_rubric_image(
        {"id": "p1", "title": "t", "image_prompt_en": "garden"},
        persona="garden",
        rubric=rubric,
        require=True,
        allow_generate=True,
    )
    assert src == "stub"
    assert path and path.endswith("stub.jpg")


def test_tick_duplicate_skip(store, monkeypatch):
    monkeypatch.setattr(
        "publisher.dispatch.notify_tick_results",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "publisher.image_gen.generate_gemini_image",
        lambda *a, **k: None,
    )
    data = store.load()
    data["mode"] = "test"
    data["posts"] = [
        {
            "id": "post-old",
            "project_id": "tg:garden",
            "title": "Дубль",
            "body": LONG_BODY,
            "rubric_id": "stepanych",
            "scheduled_at": "2026-08-30 12:00",
            "status": "test_sent",
            "created_at": "2026-08-30T09:00:00+00:00",
            "published_at": "2026-08-30T09:01:00+00:00",
        },
        {
            "id": "post-new",
            "project_id": "tg:garden",
            "title": "Дубль",
            "body": LONG_BODY,
            "rubric_id": "stepanych",
            "scheduled_at": "2026-09-02 12:00",
            "status": "scheduled",
            "created_at": "2026-09-01T09:00:00+00:00",
        },
    ]
    store.save(data)
    result = tick(store, now=datetime(2026, 9, 2, 12, 1, tzinfo=MSK), fill_bank=False)
    assert result["sent"]
    assert result["sent"][0]["skipped"] is True
    assert "duplicate" in (result["sent"][0]["detail"] or "")


def test_studio_gemini_import(client):
    pack = f"""---
rubric: lunar
headline: Импорт тест
---
{LONG_BODY}
"""
    r = client.post(
        "/admin/studio/api/import/gemini",
        data={"project_id": "tg:garden", "text": pack},
    )
    assert r.status_code == 200
    assert r.json()["added"] == 1
