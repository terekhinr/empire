#!/usr/bin/env python3
"""Импорт Gdepar/Stern из «грязной» вставки (без ---, как копирует Gemini).

Использование:
  # из файла
  ./venv/bin/python tools/ingest_gdepar_paste.py my_paste.txt

  # из stdin (вставил в терминал, Ctrl+D)
  ./venv/bin/python tools/ingest_gdepar_paste.py

  # один пост — попроси Gemini: «только пост duo_pr_019_b02, полный текст»
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "docs" / "content_factory" / "gemini_export"
IMPORT_RAW = ROOT / "data" / "gdepar_duo_curated_import_raw.md"

FM_KEYS = ("id", "pool", "slot", "tag", "headline", "hashtags", "image_file", "topic_raw", "image_prompt_en", "rubric_tag")
FM_KEY_ALT = "|".join(FM_KEYS)


def _expand_inline_meta(first_line: str) -> list[str]:
    """Gemini часто копирует `id: … slot: … topic_raw: …` в одну строку."""
    line = first_line.strip()
    if not line.lower().startswith("id:"):
        return [line]
    if not re.search(rf"\b(?:slot|pool|topic_raw|headline|tag):", line, re.I):
        return [line]
    meta: list[str] = []
    for m in re.finditer(rf"\b({FM_KEY_ALT}):\s*", line, re.I):
        key = m.group(1).lower()
        start = m.end()
        nxt = re.search(rf"\s+(?:{FM_KEY_ALT}):", line[start:], re.I)
        val = (line[start : start + nxt.start()] if nxt else line[start:]).strip()
        meta.append(f"{key}: {val}")
    return meta or [line]


def _normalize_stern_body(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            out.append("")
            continue
        if s.startswith("🏛️") and "<b>" not in s:
            title = s.lstrip("🏛️").strip()
            out.append(f"🏛️ <b>{title}</b>" if title else s)
            continue
        out.append(line.rstrip())
    return "\n".join(out).strip()

SPLIT_RE = re.compile(r"\n(?=id:\s*(?:duo_|stern_))", re.IGNORECASE)
VALID_ID_RE = re.compile(r"^id:\s*(?:duo_[a-z0-9_]+|stern_\d{4}_[a-z0-9_]+)$", re.I | re.M)


def _valid_post_id(block: str) -> bool:
    m = re.search(r"^id:\s*(\S+)", block, re.M | re.I)
    if not m:
        return False
    pid = m.group(1)
    if pid.endswith("..."):
        return False
    return bool(re.match(r"^(?:duo_[a-z0-9_]+|stern_\d{4}_[a-z0-9_]+)$", pid, re.I))


def _strip_checklist(text: str) -> str:
    """Убрать блоки CHECKLIST между постами; не резать по первому вхождению в boot/задании."""
    text = re.sub(
        r"\n(?:## )?CHECKLIST\s*\nPOST_COUNT:.*?(?=\n\nid:\s*(?:duo_|stern_)|\Z)",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Хвостовой checklist (последний батч)
    text = re.sub(r"\n(?:## )?CHECKLIST\s*\nPOST_COUNT:.*\Z", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def _strip_paste_noise(text: str) -> str:
    """Boot MSG1, шаблоны заданий и примеры до первого реального поста Gemini."""
    m = re.search(r"^id:\s*stern_1900_ev_\d+_b\d+\s+slot:\s*\d+", text, re.M | re.I)
    if m:
        text = text[m.start() :]
    else:
        m = re.search(r"^id:\s*duo_[a-z0-9_]+\s+(?:pool|slot):", text, re.M | re.I)
        if m:
            text = text[m.start() :]
    # Убрать повторные заголовки заданий между батчами
    text = re.sub(
        r"# ЗАДАНИЕ:.*?(?=^id:\s*(?:duo_|stern_))",
        "",
        text,
        flags=re.M | re.S,
    )
    return text.strip()


def _normalize_body(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            out.append("")
            continue
        if s.startswith("🔥") and "**" not in s:
            title = s.lstrip("🔥").strip()
            out.append(f"🔥 **{title}**" if title else s)
            continue
        if re.match(r"^(Михалыч|Кириллыч):", s) and not s.startswith("**"):
            who, _, rest = s.partition(":")
            out.append(f"**{who.strip()}:**{rest}")
            continue
        out.append(line.rstrip())
    return "\n".join(out).strip()


def parse_loose_posts(text: str) -> list[str]:
    text = _strip_paste_noise(_strip_checklist(text))
    if not text.strip():
        return []
    chunks = SPLIT_RE.split(text.strip())
    blocks: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.lower().startswith("id:"):
            continue
        lines = chunk.splitlines()
        meta_lines = _expand_inline_meta(lines[0])
        i = 1
        if len(meta_lines) == 1 and meta_lines[0] == lines[0].strip():
            meta_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    i += 1
                    break
                m = re.match(r"^(\w+):\s*(.*)$", line)
                if m and m.group(1).lower() in FM_KEYS:
                    meta_lines.append(line)
                    i += 1
                    continue
                break
        else:
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    i += 1
                    break
                m = re.match(r"^(\w+):\s*(.*)$", line)
                if m and m.group(1).lower() in FM_KEYS:
                    meta_lines.append(line)
                    i += 1
                    continue
                break
        body_raw = "\n".join(lines[i:])
        body = _normalize_body(body_raw)
        if re.search(r"^id:\s*stern_", chunk, re.M | re.I):
            body = _normalize_stern_body(body_raw)
        if not meta_lines or not body or not _valid_post_id(chunk):
            continue
        fm = "\n".join(meta_lines)
        blocks.append(f"---\n{fm}\n---\n\n{body}")
    return blocks


def main() -> int:
    if len(sys.argv) > 1:
        raw = Path(sys.argv[1]).read_text(encoding="utf-8")
        label = Path(sys.argv[1]).stem
    else:
        raw = sys.stdin.read()
        label = "paste"

    posts = parse_loose_posts(raw)
    if not posts:
        print("ERROR: 0 постов — проверь, что текст начинается с id: duo_... или id: stern_...")
        return 1

    gdepar_blocks, stern_blocks = [], []
    for p in posts:
        if re.search(r"^id:\s*duo_", p, re.M | re.I):
            gdepar_blocks.append(p)
        elif re.search(r"^id:\s*stern_", p, re.M | re.I):
            stern_blocks.append(p)

    out_name = f"gemini-code-{label}.md"
    out_path = EXPORT / out_name
    out_path.write_text("\n\n".join(posts) + "\n", encoding="utf-8")
    print(f"OK parsed {len(posts)} posts → {out_path}")

    if gdepar_blocks:
        header = "# Paste import\n\n"
        IMPORT_RAW.write_text(header + "\n\n---\n\n".join(gdepar_blocks) + "\n", encoding="utf-8")
        subprocess.run(
            [str(ROOT / "venv" / "bin" / "python"), str(ROOT / "scripts" / "parse_gdepar_duo_import.py")],
            check=True,
            cwd=str(ROOT),
        )
        print(f"OK gdepar +{len(gdepar_blocks)}")

    if stern_blocks:
        stern_out = ROOT / "docs/content_factory/gemini_export/generated/stern_all_ingested.md"
        existing = stern_out.read_text(encoding="utf-8") if stern_out.is_file() else "# Stern paste\n\n"
        stern_out.write_text(existing.rstrip() + "\n\n---\n\n".join(stern_blocks) + "\n", encoding="utf-8")
        subprocess.run(
            [str(ROOT / "venv" / "bin" / "python"), str(ROOT / "scripts" / "parse_stern_curated_import.py")],
            check=True,
            cwd=str(ROOT),
        )
        print(f"OK stern +{len(stern_blocks)}")

    subprocess.run([str(ROOT / "venv" / "bin" / "python"), str(ROOT / "tools/ingest_gemini_content_export.py")], cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
