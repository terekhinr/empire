"""Тест импорта Obsidian-подобных .md в JSON-очередь."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_strip_yaml_scalar_nested_quotes():
    from scripts.import_obsidian_queue import _strip_yaml_scalar

    assert _strip_yaml_scalar('\'"Можно ли?"\'') == "Можно ли?"
    assert _strip_yaml_scalar('"Заголовок"') == "Заголовок"


def test_import_empire_only_queue_folders():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        empire = Path(tmp) / "Empire"
        (empire / "pension" / "queue").mkdir(parents=True)
        (empire / "pension" / "inbox").mkdir()
        (empire / "_templates").mkdir()
        (empire / "pension" / "queue" / "post.md").write_text(
            "---\nid: q1\npersona: pension\ntitle: Q\nstatus: ready\n---\n\nТело.",
            encoding="utf-8",
        )
        (empire / "pension" / "inbox" / "draft.md").write_text("---\nid: d1\n---\n\nНе импорт.", encoding="utf-8")
        (empire / "_templates" / "obsidian_pension_post.md").write_text("---\nstatus: draft\n---\n", encoding="utf-8")
        (empire / "pension" / "queue" / "_template.md").write_text("---\n---\n", encoding="utf-8")
        out_json = Path(tmp) / "queue.json"
        env = os.environ.copy()
        env["OBSIDIAN_EMPIRE_INCOMING"] = str(empire)
        env["OBSIDIAN_IMPORT_QUEUE_OUT"] = str(out_json)
        subprocess.run(
            [sys.executable, str(root / "scripts" / "import_obsidian_queue.py")],
            cwd=str(root),
            env=env,
            check=True,
        )
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["id"] == "q1"


def test_dedupe_duplicate_ids_prefers_ready():
    from scripts.import_obsidian_queue import dedupe_queue_rows

    rows = dedupe_queue_rows(
        [
            {
                "id": "same-id",
                "source_path": "/a/draft.md",
                "status": "draft",
                "scheduled": "2026-06-10 11:00",
                "body_markdown": "short",
            },
            {
                "id": "same-id",
                "source_path": "/a/ready.md",
                "status": "ready",
                "scheduled": "2026-06-10 12:00",
                "body_markdown": "longer body text",
            },
        ]
    )
    assert len(rows) == 1
    assert rows[0]["source_path"] == "/a/ready.md"
    assert rows[0]["scheduled"] == "2026-06-10 12:00"


def test_import_writes_queue():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        inc = Path(tmp) / "in"
        inc.mkdir()
        (inc / "hello.md").write_text(
            "---\nid: test-1\npersona: pension\ntitle: Привет\n---\n\nТело **жирное**.",
            encoding="utf-8",
        )
        out_json = Path(tmp) / "queue.json"
        env = os.environ.copy()
        env["OBSIDIAN_EMPIRE_INCOMING"] = str(inc)
        env["OBSIDIAN_IMPORT_QUEUE_OUT"] = str(out_json)
        subprocess.run(
            [sys.executable, str(root / "scripts" / "import_obsidian_queue.py")],
            cwd=str(root),
            env=env,
            check=True,
        )
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert any(r.get("id") == "test-1" for r in data)
        row = next(r for r in data if r.get("id") == "test-1")
        assert row["persona"] == "pension"
        assert "Тело" in row["body_markdown"]
