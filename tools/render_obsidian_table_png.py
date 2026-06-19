#!/usr/bin/env python3
"""Рендер markdown-таблицы в PNG для Telegram (читаемо на мобильном)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
_TABLE_SEP = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")


def _split_row(line: str) -> list[str]:
    s = line.strip().strip("|")
    return [re.sub(r"\*\*(.+?)\*\*", r"\1", c.strip()) for c in s.split("|")]


def parse_markdown_table(text: str) -> tuple[list[str], list[list[str]]] | None:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "|" in line and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            header = _split_row(line)
            rows = []
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append(_split_row(lines[j]))
                j += 1
            return header, rows
    return None


def render_table_png(
    header: list[str],
    rows: list[list[str]],
    out_path: Path,
    *,
    title: str = "",
) -> Path:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    font_bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font = ImageFont.truetype(next(p for p in font_paths if Path(p).exists()), 18)
    font_b = ImageFont.truetype(next(p for p in font_bold_paths if Path(p).exists()), 18)
    font_title = ImageFont.truetype(next(p for p in font_bold_paths if Path(p).exists()), 22)

    short_h = ["№", "Направление", "Мест", "Заявл.", "Зач."]
    data = []
    for row in rows:
        cells = row + [""] * max(0, len(header) - len(row))
        data.append([cells[0], cells[1], cells[2], cells[3], cells[4]])

    col_w = [36, 420, 88, 88, 88]
    row_h = 34
    pad = 16
    title_h = 40 if title else 0
    h = pad * 2 + title_h + row_h * (1 + len(data))
    w = pad * 2 + sum(col_w)

    img = Image.new("RGB", (w, h), "#1e2a3a")
    draw = ImageDraw.Draw(img)
    y = pad
    if title:
        draw.text((pad, y), title, fill="#ffffff", font=font_title)
        y += title_h

    x0 = pad
    for i, label in enumerate(short_h):
        x = x0 + sum(col_w[:i])
        draw.rectangle([x, y, x + col_w[i], y + row_h], outline="#3d5166", fill="#263545")
        draw.text((x + 8, y + 8), label, fill="#8ab4f8", font=font_b)

    y += row_h
    for ri, row in enumerate(data):
        bg = "#1e2a3a" if ri % 2 == 0 else "#243040"
        for ci, cell in enumerate(row):
            x = x0 + sum(col_w[:ci])
            draw.rectangle([x, y, x + col_w[ci], y + row_h], outline="#3d5166", fill=bg)
            f = font_b if ci == 1 else font
            text = cell[:48] + ("…" if len(cell) > 48 else "")
            draw.text((x + 8, y + 8), text, fill="#e8eaed", font=f)
        y += row_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: render_obsidian_table_png.py <md_file> <out.png> [title]", file=sys.stderr)
        return 1
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    body = md.split("---", 2)[-1] if md.startswith("---") else md
    parsed = parse_markdown_table(body)
    if not parsed:
        print("No markdown table found", file=sys.stderr)
        return 1
    header, rows = parsed
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    render_table_png(header, rows, Path(sys.argv[2]), title=title)
    print(sys.argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
