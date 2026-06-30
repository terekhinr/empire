#!/usr/bin/env python3
"""Собрать манифест картинок + paste-запросы для Gemini Nano Banana.

  ./venv/bin/python tools/build_nanobanana_image_manifest.py
  ./venv/bin/python tools/build_nanobanana_image_manifest.py --channel stern
  ./venv/bin/python tools/build_nanobanana_image_manifest.py --dry-run

Выход:
  data/curated_topic_images_manifest.json
  docs/content_factory/gemini_export/image_batch_requests/{channel}_images_partN.txt
  docs/content_factory/gemini_export/gemini_IMAGE_MANIFEST.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from curated_image_lib import (
    GDEPAR_MATRIX,
    EXPORT,
    MANIFEST_PATH,
    STERN_MATRIX,
    audit_gdepar_classic_banya,
    build_full_prompt,
    classic_banya_manifest_items,
    gdepar_dir_for_post,
    gdepar_scene_hint,
    hashtag_theme,
    load_json,
    load_stern_ingested_prompts,
    load_styles,
    manifest_item,
    stern_canonical_topic_id,
    stern_scene_hint,
    topic_id_from_stern_post_id,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = EXPORT / "image_batch_requests"
OUT_MD = EXPORT / "gemini_IMAGE_MANIFEST.md"
CHUNK = 6


def _load_stern_curated() -> list[dict]:
    p = ROOT / "data" / "stern_curated.json"
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("entries") or [])


def _load_gdepar_curated() -> list[dict]:
    p = ROOT / "data" / "gdepar_duo_curated.json"
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("entries") or [])


def build_gdepar_items(styles: dict) -> list[dict]:
    matrix = load_json(GDEPAR_MATRIX)
    items: list[dict] = []
    matrix_ids: set[str] = set()
    for pool in ("practice", "evening", "banya_week"):
        for entry in matrix.get(pool) or []:
            tid = entry["id"]
            matrix_ids.add(tid)
            scene = gdepar_scene_hint(entry, styles)
            items.append(
                manifest_item(
                    channel="gdepar",
                    topic_id=tid,
                    topic_raw=entry.get("headline", tid),
                    scene_en=scene,
                    bind_key=tid,
                    bind_mode="topic_id",
                    pool=pool,
                    styles=styles,
                )
            )

    curated = _load_gdepar_curated()
    for post in curated:
        pid = post.get("id") or ""
        if not pid:
            continue
        m = re.match(r"duo_([a-z]+)_(\d+)_", pid, re.I)
        if m and f"GDP-{m.group(1).upper()}-{m.group(2)}" in matrix_ids:
            continue
        headline = (post.get("headline") or pid).strip()
        tag = post.get("tag") or ""
        d = gdepar_dir_for_post(tag, headline)
        scene = gdepar_scene_hint({"dir": d, "headline": headline}, styles)
        items.append(
            manifest_item(
                channel="gdepar",
                topic_id=pid,
                topic_raw=headline,
                scene_en=scene,
                bind_key=pid,
                bind_mode="post",
                post_ids=[pid],
                pool=post.get("pool"),
                styles=styles,
            )
        )
    return items


def build_stern_items(styles: dict) -> list[dict]:
    ingested = load_stern_ingested_prompts()
    curated = _load_stern_curated()
    items: list[dict] = []
    seen_canonical: set[str] = set()

    # Вечер: 15 канонических картинок на базовые STR-EV-001…015
    matrix = load_json(STERN_MATRIX)
    ev_topics = matrix.get("evening_1900") or []
    post_ids_by_canonical: dict[str, list[str]] = defaultdict(list)
    for post in curated:
        if str(post.get("slot")) != "1900":
            continue
        pid = post.get("id") or ""
        tid = topic_id_from_stern_post_id(pid)
        if not tid or not tid.startswith("STR-EV"):
            continue
        canon = stern_canonical_topic_id(tid, "ev")
        post_ids_by_canonical[canon].append(pid)

    for entry in ev_topics:
        tid = entry["id"]
        canon = stern_canonical_topic_id(tid, "ev")
        if canon in seen_canonical:
            continue
        seen_canonical.add(canon)
        base_raw = next(
            (e["topic_raw"] for e in ev_topics if e["id"] == canon),
            entry.get("topic_raw", ""),
        )
        sample_pid = (post_ids_by_canonical.get(canon) or [None])[0]
        scene = ingested.get(sample_pid or "", "") or stern_scene_hint(base_raw)
        items.append(
            manifest_item(
                channel="stern",
                topic_id=canon,
                topic_raw=base_raw,
                scene_en=scene,
                bind_key=canon,
                bind_mode="canonical_evening",
                post_ids=sorted(post_ids_by_canonical.get(canon, [])),
                pool="1900",
                styles=styles,
            )
        )

    # Утро: своя картинка на каждый пост 0930
    for post in curated:
        if str(post.get("slot")) != "0930":
            continue
        pid = post.get("id") or ""
        topic_raw = post.get("topic_raw") or pid
        tid = topic_id_from_stern_post_id(pid) or pid
        scene = ingested.get(pid, "") or post.get("image_prompt_en") or stern_scene_hint(topic_raw)
        items.append(
            manifest_item(
                channel="stern",
                topic_id=tid if tid.startswith("STR-") else pid,
                topic_raw=topic_raw,
                scene_en=scene,
                bind_key=pid,
                bind_mode="post",
                post_ids=[pid],
                pool="0930",
                styles=styles,
            )
        )
    return items


def build_paste_batch(channel: str, batch_items: list[dict], part: int) -> str:
    ch_label = (load_styles().get("channels") or {}).get(channel, {}).get("label", channel)
    lines = [
        f"# ЗАДАНИЕ: {channel}_images_part{part:02d}",
        "",
        f"Сгенерируй **ровно** картинок: **{len(batch_items)}**.",
        "",
        f"CHANNEL: {channel} ({ch_label})",
        "MODEL: Gemini Nano Banana (flash image)",
        "",
        "Правила:",
        "- Одна картинка на блок `topic_id:`",
        "- Без текста на изображении, без водяных знаков",
        "- Сохрани файлы с именами из `filename:`",
        "- Формат ответа: приложи каждую картинку сразу после её блока",
        "",
        "Блок одной картинки:",
        "```",
        f"topic_id: {batch_items[0]['topic_id']}",
        f"filename: {Path(batch_items[0]['output_file']).name}",
        f"aspect: {batch_items[0].get('aspect_ratio', '4:3')}",
        "",
        "PROMPT:",
        "{полный промпт EN}",
        "```",
        "",
        "---",
        "",
    ]
    ids = []
    for it in batch_items:
        fname = Path(it["output_file"]).name
        lines.extend(
            [
                f"topic_id: {it['topic_id']}",
                f"filename: {fname}",
                f"aspect: {it.get('aspect_ratio', '4:3')}",
                "",
                "PROMPT:",
                it["prompt_en"],
                "",
                "---",
                "",
            ]
        )
        ids.append(it["topic_id"])
    lines.extend(
        [
            "## CHECKLIST",
            f"IMAGE_COUNT: {len(batch_items)}",
            f"IDS: {', '.join(ids)}",
            "",
        ]
    )
    return "\n".join(lines)


def write_batches(channel: str, items: list[dict]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    chunks = [items[i : i + CHUNK] for i in range(0, len(items), CHUNK)]
    for n, chunk in enumerate(chunks, 1):
        text = build_paste_batch(channel, chunk, n)
        path = OUT_DIR / f"{channel}_images_part{n:02d}.txt"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def write_summary_md(all_items: list[dict], batch_paths: list[Path], classic_audit: dict) -> None:
    by_ch: dict[str, int] = defaultdict(int)
    nanobanana_items = [i for i in all_items if not i.get("skip_nanobanana")]
    for it in nanobanana_items:
        by_ch[it["channel"]] += 1
    classic_n = sum(1 for i in all_items if i.get("rubrique") == "classic_banya")
    classic_ok = sum(1 for i in all_items if i.get("rubrique") == "classic_banya" and i.get("status") == "existing")
    lines = [
        "# Манифест картинок Nano Banana",
        "",
        f"Задач Nano Banana: **{len(nanobanana_items)}**",
        f"Классическая баня (уже готово, **не печатать**): **{classic_ok}/{classic_n}**",
        "",
        "| Канал | Nano Banana |",
        "|-------|-------------|",
    ]
    for ch, n in sorted(by_ch.items()):
        lines.append(f"| {ch} | {n} |")
    lines.extend(
        [
            "",
            "## Gdepar: Классическая баня (15:00)",
            "",
            f"- Данные: `{classic_audit.get('data_file', 'data/gdepar_classic_banya.json')}`",
            f"- Портреты: `{classic_audit.get('media_dir', 'media/gdepar/classic')}/{{id}}.jpg`",
            f"- На диске: **{classic_audit.get('on_disk', 0)}** / {classic_audit.get('entries', 0)}",
            "- Источник: Wikipedia/Commons (`ensure_classic_image`), **не** Nano Banana",
            "- Prefetch: `./venv/bin/python scripts/prefetch_gdepar_classic_images.py`",
            "",
            "## Paste-батчи (только duo + stern)",
            "",
        ]
    )
    for p in batch_paths:
        lines.append(f"- `{p.relative_to(ROOT)}`")
    lines.extend(
        [
            "",
            "## После генерации",
            "",
            "1. Положите JPG в пути из `output_file` (или в `media/_nanobanana_drop/` и запустите import).",
            "2. `./venv/bin/python tools/apply_curated_images.py`",
            "3. Или API: `./venv/bin/python tools/generate_curated_images_nanobanana.py`",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", choices=("stern", "gdepar", "all"), default="all")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    styles = load_styles()
    items: list[dict] = []
    if args.channel in ("gdepar", "all"):
        items.extend(build_gdepar_items(styles))
    if args.channel in ("stern", "all"):
        items.extend(build_stern_items(styles))

    classic_audit = audit_gdepar_classic_banya()
    classic_items = classic_banya_manifest_items() if args.channel in ("gdepar", "all") else []
    all_items = items + classic_items

    if args.dry_run:
        print(f"would write {len(items)} nanobanana + {len(classic_items)} classic (existing)")
        print(f"  classic on disk: {classic_audit.get('on_disk')}/{classic_audit.get('entries')}")
        for ch in ("gdepar", "stern"):
            n = sum(1 for i in items if i["channel"] == ch)
            print(f"  {ch} nanobanana: {n}")
        return 0

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": "Nano Banana: duo+stern. classic_banya — status existing, skip_nanobanana.",
        "generated_by": "tools/build_nanobanana_image_manifest.py",
        "classic_banya_audit": classic_audit,
        "items": all_items,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK manifest {len(items)} nanobanana + {len(classic_items)} classic → {MANIFEST_PATH}")
    print(f"OK classic banya portraits: {classic_audit.get('on_disk')}/{classic_audit.get('entries')} on disk")

    batch_paths: list[Path] = []
    for ch in sorted({i["channel"] for i in items}):
        ch_items = [i for i in items if i["channel"] == ch]
        batch_paths.extend(write_batches(ch, ch_items))
        print(f"OK {ch}: {len(ch_items)} images → {len(ch_items) // CHUNK + (1 if len(ch_items) % CHUNK else 0)} paste files")

    write_summary_md(all_items, batch_paths, classic_audit)
    print(f"OK summary → {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
