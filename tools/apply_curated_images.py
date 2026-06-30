#!/usr/bin/env python3
"""Прописать image_file в curated JSON после печки картинок.

  ./venv/bin/python tools/apply_curated_images.py
  ./venv/bin/python tools/apply_curated_images.py --dry-run

Читает data/curated_topic_images_manifest.json и обновляет:
  - data/stern_curated.json
  - data/gdepar_duo_curated.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "curated_topic_images_manifest.json"
STERN_PATH = ROOT / "data" / "stern_curated.json"
GDEPAR_PATH = ROOT / "data" / "gdepar_duo_curated.json"


def _topic_from_gdepar_id(post_id: str) -> str | None:
    m = re.match(r"duo_([a-z]+)_(\d+)_", post_id, re.I)
    if not m:
        return None
    return f"GDP-{m.group(1).upper()}-{m.group(2)}"


STERN_MATRIX = ROOT / "docs" / "content_factory" / "gemini_export" / "stern_topic_matrix.json"


def _norm_topic_raw(topic_raw: str) -> str:
    t = re.sub(r"\s*\(вариант\s+\d+\)\s*", "", (topic_raw or ""), flags=re.I).strip().lower()
    return t


def _stern_ev_by_topic() -> dict[str, str]:
    if not STERN_MATRIX.is_file():
        return {}
    data = json.loads(STERN_MATRIX.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in data.get("evening_1900") or []:
        tid = entry.get("id") or ""
        raw = entry.get("topic_raw") or ""
        if not tid.startswith("STR-EV-") or not raw:
            continue
        n = int(tid.split("-")[-1])
        canon = f"STR-EV-{(n - 1) % 15 + 1:03d}"
        out.setdefault(_norm_topic_raw(raw), canon)
    return out


def _topic_from_stern_post(post_id: str) -> str | None:
    m = re.match(r"stern_1900_ev_(\d+)_", post_id, re.I)
    if m:
        return f"STR-EV-{int(m.group(1)):03d}"
    return None


def apply_stern(entries: list[dict], by_bind: dict[str, str], dry: bool) -> int:
    ev_by_topic = _stern_ev_by_topic()
    n = 0
    for e in entries:
        pid = e.get("id") or ""
        slot = str(e.get("slot") or "")
        path = None
        if slot == "0930":
            path = by_bind.get(pid)
        elif slot == "1900":
            tid = _topic_from_stern_post(pid)
            if tid:
                canon = f"STR-EV-{(int(tid.split('-')[-1]) - 1) % 15 + 1:03d}"
                path = by_bind.get(canon) or by_bind.get(tid)
            if not path:
                ev = ev_by_topic.get(_norm_topic_raw(e.get("topic_raw") or ""))
                if ev:
                    path = by_bind.get(ev)
        if path and e.get("image_file") != path:
            e["image_file"] = path
            n += 1
    return n


def apply_gdepar(entries: list[dict], by_topic: dict[str, str], by_post: dict[str, str], dry: bool) -> int:
    n = 0
    for e in entries:
        pid = e.get("id") or ""
        tid = _topic_from_gdepar_id(pid)
        path = by_post.get(pid) or (by_topic.get(tid) if tid else None)
        if path and e.get("image_file") != path:
            e["image_file"] = path
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not MANIFEST.is_file():
        print(f"Нет {MANIFEST}")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_bind: dict[str, str] = {}
    by_topic: dict[str, str] = {}
    by_post: dict[str, str] = {}

    for it in manifest.get("items") or []:
        if it.get("skip_nanobanana") or it.get("rubrique") == "classic_banya":
            continue
        out = it.get("output_file")
        if not out:
            continue
        full = ROOT / out
        if not full.is_file():
            continue
        rel = out
        ch = it.get("channel")
        if ch == "stern":
            mode = it.get("bind_mode")
            if mode == "post":
                for pid in it.get("post_ids") or [it.get("bind_key")]:
                    if pid:
                        by_bind[pid] = rel
            else:
                by_bind[it["topic_id"]] = rel
        elif ch == "gdepar":
            mode = it.get("bind_mode")
            if mode == "post":
                for pid in it.get("post_ids") or [it.get("bind_key")]:
                    if pid:
                        by_post[pid] = rel
            else:
                by_topic[it["topic_id"]] = rel

    stern_n = gdepar_n = 0
    if STERN_PATH.is_file():
        data = json.loads(STERN_PATH.read_text(encoding="utf-8"))
        entries = data.get("entries") or []
        stern_n = apply_stern(entries, by_bind, args.dry_run)
        if not args.dry_run and stern_n:
            data["entries"] = entries
            STERN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if GDEPAR_PATH.is_file():
        data = json.loads(GDEPAR_PATH.read_text(encoding="utf-8"))
        entries = data.get("entries") or []
        gdepar_n = apply_gdepar(entries, by_topic, by_post, args.dry_run)
        if not args.dry_run and gdepar_n:
            data["entries"] = entries
            GDEPAR_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"stern image_file updated: {stern_n}")
    print(f"gdepar image_file updated: {gdepar_n}")
    nanobanana_items = [
        i for i in manifest.get("items") or []
        if not i.get("skip_nanobanana")
    ]
    missing = sum(
        1
        for it in nanobanana_items
        if it.get("output_file") and not (ROOT / it["output_file"]).is_file()
    )
    if missing:
        print(f"WARN: {missing} файлов из манифеста ещё не на диске")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
