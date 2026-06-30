#!/usr/bin/env python3
"""Собрать посты из docs/audit/gemini_export/gemini-code-*.md в Empire."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIRS = (
    ROOT / "docs" / "audit" / "gemini_export",
    ROOT / "docs" / "content_factory" / "gemini_export",
)
GEN = ROOT / "docs" / "content_factory" / "gemini_export" / "generated"
GDEPAR_IMPORT = ROOT / "data" / "gdepar_duo_curated_import_raw.md"
STERN_OUT = GEN / "stern_all_ingested.md"
STATUS = GEN / "GEMINI_OUTPUT_STATUS.md"

TRUNC_MARKERS = ("остальные посты", "и так далее", "Для краткости")


def split_posts(text: str) -> list[str]:
    """Полные блоки поста (frontmatter + body) в формате Gemini."""
    start = text.find("---\n")
    if start < 0:
        return []
    blob = text[start:]
    out: list[str] = []
    for fm_raw, body in POST_BLOCK_RE.findall(blob):
        out.append(f"---\n{fm_raw}\n---\n{body}".strip())
    return out


POST_BLOCK_RE = re.compile(
    r"---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\nid:|\Z)",
    re.DOTALL,
)


def is_truncated_file(text: str) -> bool:
    return any(m in text for m in TRUNC_MARKERS)


def frontmatter(post: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", post, re.DOTALL)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def main() -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    raw_dir = GEN / "raw"
    raw_dir.mkdir(exist_ok=True)

    gdepar_blocks: list[str] = []
    stern_blocks: list[str] = []
    truncated_files: list[str] = []
    seen_ids: set[str] = set()
    dup_ids: list[str] = []
    source_files: list[Path] = []

    for src in SRC_DIRS:
        if not src.is_dir():
            continue
        source_files.extend(sorted(src.glob("gemini-code-*.md")))

    for fp in source_files:
        shutil.copy2(fp, raw_dir / fp.name)
        text = fp.read_text(encoding="utf-8")
        if is_truncated_file(text):
            truncated_files.append(fp.name)
        for post in split_posts(text):
            meta = frontmatter(post)
            pid = meta.get("id", "")
            if pid in seen_ids:
                dup_ids.append(pid)
                continue
            seen_ids.add(pid)
            if pid.startswith("duo_"):
                gdepar_blocks.append(post)
            elif pid.startswith("stern_"):
                stern_blocks.append(post)

    # merge gdepar into import (append to existing raw if any)
    header = (
        "# Импорт из Gemini (автосборка)\n\n"
        "<!-- tools/ingest_gemini_content_export.py -->\n\n"
    )
    GDEPAR_IMPORT.write_text(
        header + "\n\n---\n\n".join(gdepar_blocks) + "\n",
        encoding="utf-8",
    )

    stern_header = "# Stern drafts from Gemini\n\n"
    STERN_OUT.write_text(
        stern_header + "\n\n---\n\n".join(stern_blocks) + "\n",
        encoding="utf-8",
    )

    # run gdepar parser
    import subprocess

    subprocess.run(
        [str(ROOT / "venv" / "bin" / "python"), str(ROOT / "scripts" / "parse_gdepar_duo_import.py")],
        check=True,
        cwd=str(ROOT),
    )
    subprocess.run(
        [str(ROOT / "venv" / "bin" / "python"), str(ROOT / "scripts" / "parse_stern_curated_import.py")],
        check=True,
        cwd=str(ROOT),
    )

    curated = json.loads((ROOT / "data" / "gdepar_duo_curated.json").read_text(encoding="utf-8"))
    n_curated = len(curated.get("entries") or [])

    src_note = ", ".join(str(d.relative_to(ROOT)) for d in SRC_DIRS if d.is_dir())
    md = [
        "# Статус выгрузки Gemini (авторазбор)",
        "",
        f"- Источники: `{src_note}`",
        f"- Файлов `gemini-code-*.md`: {len(source_files)}",
        f"- **Gdepar постов собрано:** {len(gdepar_blocks)}",
        f"- **Stern постов собрано:** {len(stern_blocks)}",
        f"- **Всего уникальных id:** {len(seen_ids)}",
        f"- **Записей в gdepar_duo_curated.json:** {n_curated}",
        "",
        "## Обрезанные файлы (перегенерировать в Gemini)",
        "",
    ]
    if truncated_files:
        md.extend(f"- `{f}`" for f in truncated_files)
    else:
        md.append("- нет")
    md += [
        "",
        "## Дубликаты id (пропущены)",
        "",
    ]
    md.extend(f"- `{d}`" for d in dup_ids) if dup_ids else md.append("- нет")
    md += [
        "",
        "## Чего не хватает до 15.09",
        "",
        "| Канал | есть | цель | осталось |",
        "|-------|------|------|----------|",
        f"| Gdepar duo | {len(gdepar_blocks)} | ~139 | {max(0, 139 - len(gdepar_blocks))} |",
        f"| Stern текст | {len(stern_blocks)} | ~149 | {max(0, 149 - len(stern_blocks))} |",
        "",
        "## Следующие батчи (манифест)",
        "",
        "- Gdepar: файлы с TRUNCATED / по 1 посту — полные батчи 02–12",
        "- Stern 1900: добить `stern_08` … `stern_13` до 12 постов в батче",
        "- Фаза 0 в выгрузке **не найдена** — опционально",
        "",
        "## Импорт",
        "",
        "- Gdepar: `data/gdepar_duo_curated.json` обновлён",
        "- Stern: `docs/content_factory/gemini_export/generated/stern_all_ingested.md`",
        "- Сырые файлы: `generated/raw/`",
        "",
        "## Замечания редактора",
        "",
        "- P0 (фейк-цифры, «слушай») в выгрузке **не найдены**.",
        "- Stern `stern_0930_yoga_tgu_66` — get-up; проверить при Modic.",
        "- Заголовок `Полки — не для слабаков` — заменить на нейтральный при approve.",
    ]
    STATUS.write_text("\n".join(md), encoding="utf-8")
    print(f"OK gdepar={len(gdepar_blocks)} stern={len(stern_blocks)} curated={n_curated}")
    print(f"→ {STATUS}")


if __name__ == "__main__":
    main()
