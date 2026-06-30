#!/usr/bin/env python3
"""Собрать copy-paste запросы для Gemini из манифеста и матриц."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "docs" / "content_factory" / "gemini_export"
MANIFEST = EXPORT / "BATCH_MANIFEST_sept2026.json"
HARD_RULES = (EXPORT / "gemini_HARD_RULES.txt").read_text(encoding="utf-8")
SLIM_RULES = (
    "Правила из gemini_PASTE_MSG1_BOOT.txt обязательны: "
    "ровно N постов, только markdown, P0 запрещён, CHECKLIST в конце."
)
SLIM_RULES_STERN = (
    "Правила из gemini_PASTE_MSG1_BOOT_STERN.txt обязательны: "
    "ровно N постов, только markdown, P0 запрещён, CHECKLIST в конце."
)
OUT_MD = EXPORT / "gemini_BATCH_REQUESTS_REDO.md"
OUT_DIR = EXPORT / "batch_requests"

# Батчи к перегенерации (остальное уже в Empire или не нужно)
REDO_BATCHES = {
    "gdepar_02",
    "gdepar_03",
    "gdepar_04",
    "gdepar_05",
    "gdepar_06",
    "gdepar_07",
    "gdepar_08",
    "gdepar_09",
    "gdepar_10",
    "gdepar_11",
    "gdepar_12",
    "stern_08",
    "stern_09",
    "stern_10",
    "stern_11",
    "stern_12",
    "stern_13",
}

CHUNK_SIZE = 6

GDEPAR_HEAD = re.compile(
    r"^\| (GDP-[A-Z]+-\d+) \| \w+ \| (.+?) \|$",
    re.MULTILINE,
)
STERN_TOPIC = re.compile(
    r"^\| (STR-[A-Z]+-\d+) \| (.+?) \|$",
    re.MULTILINE,
)


def load_gdepar_topics() -> dict[str, str]:
    text = (EXPORT / "gdepar_POST_MATRIX_FULL.md").read_text(encoding="utf-8")
    return {m.group(1): m.group(2).strip() for m in GDEPAR_HEAD.finditer(text)}


def load_stern_topics() -> dict[str, str]:
    text = (EXPORT / "stern_POST_MATRIX_FULL.md").read_text(encoding="utf-8")
    return {m.group(1): m.group(2).strip() for m in STERN_TOPIC.finditer(text)}


def load_existing_ids() -> set[str]:
    ids: set[str] = set()
    existing = EXPORT / "EXISTING_gdepar_duo.json"
    if existing.is_file():
        data = json.loads(existing.read_text(encoding="utf-8"))
        for e in data.get("entries") or []:
            if e.get("id"):
                ids.add(e["id"])
    ingested = EXPORT / "generated" / "stern_all_ingested.md"
    if ingested.is_file():
        for m in re.finditer(r"^id:\s*(\S+)", ingested.read_text(encoding="utf-8"), re.M):
            ids.add(m.group(1))
    import_raw = ROOT / "data" / "gdepar_duo_curated_import_raw.md"
    if import_raw.is_file():
        for m in re.finditer(r"^id:\s*(\S+)", import_raw.read_text(encoding="utf-8"), re.M):
            ids.add(m.group(1))
    return ids


def topic_slug(topic_id: str) -> str:
    """GDP-PR-013 → pr_013, STR-EV-001 → ev_001."""
    parts = topic_id.split("-")
    if len(parts) >= 3:
        return f"{parts[1].lower()}_{parts[2]}"
    return topic_id.lower().replace("-", "_")


def gdepar_id(topic_id: str, headline: str, batch_id: str) -> str:
    b = batch_id.split("_")[-1]
    return f"duo_{topic_slug(topic_id)}_b{b}"


def stern_id(slot: str, topic_id: str, batch_id: str) -> str:
    b = batch_id.split("_")[-1]
    return f"stern_{slot}_{topic_slug(topic_id)}_b{b}"


def chunk_topics(topic_ids: list[str], size: int) -> list[list[str]]:
    return [topic_ids[i : i + size] for i in range(0, len(topic_ids), size)]


def build_gdepar_request(
    batch: dict,
    part_label: str,
    topic_ids: list[str],
    gdepar_topics: dict[str, str],
    existing: set[str],
) -> str:
    pool = batch.get("pool") or batch.get("slot", "")
    bid = batch["batch_id"]
    lines = [
        f"# ЗАДАНИЕ: {bid}_{part_label}",
        "",
        "Сгенерируй **ровно** постов: **" + str(len(topic_ids)) + "**.",
        "",
        f"BATCH_ID: {bid}",
        f"POOL: {pool}",
        f"PART: {part_label}",
        "",
        "TOPIC_IDS и заголовки (по 1 посту на строку):",
        "",
    ]
    id_hints: list[str] = []
    for tid in topic_ids:
        hl = gdepar_topics.get(tid, tid)
        suggested = gdepar_id(tid, hl, bid)
        id_hints.append(suggested)
        lines.append(f"- `{tid}` → headline: **{hl}** → id: `{suggested}`")
    lines += [
        "",
        "УЖЕ ЕСТЬ Gdepar (не повторять id):",
        ", ".join(sorted(x for x in existing if x.startswith("duo_"))),
        "",
        "Формат поста:",
        "```",
        "---",
        "id: duo_{slug}",
        f"pool: {pool}",
        "tag: {тег}",
        "headline: {без эмодзи}",
        "hashtags: #баня #гдепар #{тег}",
        "image_file: null",
        "---",
        "",
        "🔥 **{Заголовок}**",
        "",
        "**Михалыч:** …",
        "",
        "**Кириллыч:** …",
        "```",
        "",
        SLIM_RULES,
        "",
        f"Имя файла в ответе: `gdepar_{bid}_{part_label}.md`",
        "",
        "## CHECKLIST (обязательно в конце)",
        f"POST_COUNT: {len(topic_ids)}",
        "P0_FOUND: 0",
        f"IDS: {', '.join(id_hints)}",
    ]
    return "\n".join(lines)


def build_stern_request(
    batch: dict,
    part_label: str,
    topic_ids: list[str],
    stern_topics: dict[str, str],
    existing: set[str],
) -> str:
    slot = batch.get("slot") or batch.get("pool", "")
    bid = batch["batch_id"]
    char_range = "350–600 знаков" if slot == "0930" else "500–900 знаков"
    lines = [
        f"# ЗАДАНИЕ: {bid}_{part_label}",
        "",
        "Сгенерируй **ровно** постов: **" + str(len(topic_ids)) + "**.",
        "",
        f"BATCH_ID: {bid}",
        f"SLOT: {slot}",
        f"PART: {part_label}",
        "",
        "TOPIC_IDS (topic_raw — дословно из матрицы):",
        "",
    ]
    id_hints: list[str] = []
    for tid in topic_ids:
        raw = stern_topics.get(tid, tid)
        suggested = stern_id(slot, tid, bid)
        id_hints.append(suggested)
        lines.append(f"- `{tid}` → `{raw}` → id: `{suggested}`")
    stern_existing = sorted(x for x in existing if x.startswith("stern_"))
    if stern_existing:
        lines += [
            "",
            f"УЖЕ ЕСТЬ Stern: **{len(stern_existing)}** постов в Empire — не повторять их id.",
        ]
    lines += [
        f"Объём: {char_range}. ≤3 хэштега.",
        "",
        "Формат:",
        "```",
        "---",
        f"id: stern_{slot}_...",
        f"slot: {slot}",
        "topic_raw: {дословно}",
        "hashtags: #снегири #штерн #{тема}",
        "image_prompt_en: {одна строка EN, photorealistic, no face}",
        "---",
        "",
        "🏛️ <b>Заголовок</b>",
        "",
        "Текст…",
        "",
        "#снегири #штерн #тема",
        "```",
        "",
        SLIM_RULES_STERN,
        "",
        f"Имя файла: `{bid}_{part_label}.md`",
        "",
        "## CHECKLIST",
        f"POST_COUNT: {len(topic_ids)}",
        "P0_FOUND: 0",
        f"IDS: {', '.join(id_hints)}",
    ]
    return "\n".join(lines)


def main() -> None:
    batches = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gdepar_topics = load_gdepar_topics()
    stern_topics = load_stern_topics()
    existing = load_existing_ids()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    toc: list[str] = [
        "# Gemini — запросы на перегенерацию батчей",
        "",
        "Новый чат: сначала `gemini_PASTE_NEW_CHAT.txt`, потом **один блок** за сообщение.",
        "",
        f"Подбатчи по ≤{CHUNK_SIZE} постов (меньше обрезок).",
        "",
        "## Очередь",
        "",
    ]

    part_index = 0
    for batch in batches:
        bid = batch["batch_id"]
        if bid not in REDO_BATCHES:
            continue
        topic_ids = batch["topic_ids"]
        chunks = chunk_topics(topic_ids, CHUNK_SIZE)
        toc.append(f"### {bid} ({batch['channel']}, {batch['count']} тем → {len(chunks)} частей)")
        for i, chunk in enumerate(chunks):
            part_label = f"part{chr(65 + i)}"  # partA, partB, …
            if batch["channel"] == "gdepar":
                body = build_gdepar_request(batch, part_label, chunk, gdepar_topics, existing)
            else:
                body = build_stern_request(batch, part_label, chunk, stern_topics, existing)
            fname = f"{bid}_{part_label}.txt"
            (OUT_DIR / fname).write_text(body, encoding="utf-8")
            toc.append(f"- [{bid}_{part_label}](batch_requests/{fname}) — {len(chunk)} постов")
            part_index += 1
        toc.append("")

    toc += [
        "---",
        "",
        "# Блоки для копипаста",
        "",
    ]

    for fp in sorted(OUT_DIR.glob("*.txt")):
        body = fp.read_text(encoding="utf-8")
        anchor = fp.stem
        toc.append(f"## {anchor}")
        toc.append("")
        toc.append("```")
        toc.append(body)
        toc.append("```")
        toc.append("")

    OUT_MD.write_text("\n".join(toc), encoding="utf-8")
    print(f"OK {part_index} requests → {OUT_DIR}")
    print(f"→ {OUT_MD}")


if __name__ == "__main__":
    main()
