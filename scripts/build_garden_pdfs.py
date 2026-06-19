#!/usr/bin/env python3
"""Сборка PDF из markdown: tripwire + гайд 4 недели (PyMuPDF, без браузера)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "data" / "garden_deliverables"
PDF_DIR = DELIV / "pdf"
CSS_PATH = PDF_DIR / "garden_print.css"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_MONO = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")

MARGIN_L = 50
MARGIN_R = 50
MARGIN_T = 52
MARGIN_B = 56
PAGE_W, PAGE_H = 595, 842  # A4 pt

SOURCES = {
    "tripwire": (
        DELIV / "garden_tripwire_7_errors.md",
        PDF_DIR / "garden_tripwire_checklist.pdf",
        "tripwire",
    ),
    "preview": (
        DELIV / "garden_tripwire_preview_3_errors.md",
        PDF_DIR / "garden_tripwire_preview_3_errors.pdf",
        "tripwire",
    ),
    "guide": (
        DELIV / "garden_guide_4weeks.md",
        PDF_DIR / "garden_guide_4weeks.pdf",
        "guide",
    ),
}


def _md_to_html(md_text: str, doc_class: str) -> str:
    from markdown_it import MarkdownIt

    html = MarkdownIt("commonmark").enable("table").render(md_text)
    if doc_class == "tripwire":
        html = re.sub(
            r"<h2>Ошибка (\d+)",
            r'<h2 class="page-break">Ошибка \1',
            html,
        )
    return html


def _wrap_html(body_html: str, *, doc_class: str, title: str) -> str:
    css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.is_file() else ""
    return (
        f'<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"/>'
        f"<title>{title}</title><style>{css}</style></head>"
        f'<body class="{doc_class}"><article>{body_html}</article></body></html>'
    )


def _md_to_plain_blocks(md: str) -> list[tuple[str, str]]:
    """(style, text) — h1|h2|h3|body|pre|bullet|hr|sp|table_row"""
    blocks: list[tuple[str, str]] = []
    in_code = False
    buf: list[str] = []
    table_rows: list[str] = []

    def flush_table():
        nonlocal table_rows
        for row in table_rows:
            blocks.append(("body", row))
        table_rows = []

    def flush_pre():
        nonlocal buf
        if buf:
            blocks.append(("pre", "\n".join(buf)))
            buf = []

    for line in md.splitlines():
        if line.strip().startswith("```"):
            flush_table()
            if in_code:
                flush_pre()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            buf.append(line)
            continue
        if "|" in line and line.strip().startswith("|"):
            if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append("  |  ".join(cells))
            continue
        flush_table()
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("#### "):
            blocks.append(("h3", line[5:].strip()))
        elif line.strip() == "---":
            blocks.append(("hr", ""))
        elif re.match(r"^[-*]\s+", line):
            blocks.append(("bullet", re.sub(r"^[-*]\s+", "", line).strip()))
        elif re.match(r"^\d+\.\s+", line):
            blocks.append(("bullet", line.strip()))
        elif line.strip():
            blocks.append(("body", line.strip()))
        else:
            blocks.append(("sp", ""))
    flush_table()
    if in_code:
        flush_pre()
    return blocks


def _clean_md_inline(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def build_pdf_from_md(md_path: Path, out_path: Path, doc_class: str) -> None:
    import fitz

    if not FONT.is_file():
        raise FileNotFoundError(f"Font not found: {FONT}")

    blocks = _md_to_plain_blocks(md_path.read_text(encoding="utf-8"))
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = float(MARGIN_T)
    font_cache: set[str] = set()

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        y = float(MARGIN_T)
        font_cache.clear()

    def font_for(style: str) -> tuple[str, Path, float]:
        if style in ("h1",):
            return "F1", FONT_BOLD, 20.0
        if style in ("h2",):
            return "F2", FONT_BOLD, 14.0
        if style in ("h3",):
            return "F3", FONT_BOLD, 12.0
        if style == "pre":
            return "FM", FONT_MONO, 8.5
        return "FB", FONT, 10.5 if style == "bullet" else 11.0

    def ensure_font(fname: str, fpath: Path):
        if fname not in font_cache:
            page.insert_font(fontname=fname, fontfile=str(fpath))
            font_cache.add(fname)

    def draw_block(style: str, text: str) -> None:
        nonlocal y, page
        if style == "sp":
            y += 8
            return
        if style == "hr":
            if y > PAGE_H - MARGIN_B - 20:
                new_page()
            page.draw_line(
                (MARGIN_L, y), (PAGE_W - MARGIN_R, y), color=(0.55, 0.7, 0.5), width=0.6
            )
            y += 16
            return

        if style == "h2" and doc_class == "tripwire" and text.startswith("Ошибка "):
            if y > MARGIN_T + 60:
                new_page()
        if style == "h1" and doc_class == "guide" and text.startswith("Неделя ") and y > MARGIN_T + 60:
            new_page()

        fname, fpath, fsize = font_for(style)
        content = _clean_md_inline(text)
        if style == "bullet":
            content = "•  " + content

        while content:
            if y > PAGE_H - MARGIN_B - fsize * 2:
                new_page()
            ensure_font(fname, fpath)
            rect = fitz.Rect(MARGIN_L, y, PAGE_W - MARGIN_R, PAGE_H - MARGIN_B)
            extra = 14 if style.startswith("h") else 0
            if style == "h1":
                y += 4
            remain = page.insert_textbox(
                rect,
                content,
                fontname=fname,
                fontsize=fsize,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            if remain < 0:
                new_page()
                ensure_font(fname, fpath)
                remain = page.insert_textbox(
                    fitz.Rect(MARGIN_L, y, PAGE_W - MARGIN_R, PAGE_H - MARGIN_B),
                    content,
                    fontname=fname,
                    fontsize=fsize,
                )
                if remain < 0:
                    raise RuntimeError(f"Block does not fit on page: {content[:80]}...")
            used = rect.height - remain
            y += used + extra + 4
            break

    for style, text in blocks:
        draw_block(style, text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()


def build_one(key: str, *, keep_html: bool = False) -> Path:
    src, out, doc_class = SOURCES[key]
    if not src.is_file():
        raise FileNotFoundError(src)
    if keep_html:
        md = src.read_text(encoding="utf-8")
        title_m = re.search(r"^#\s+(.+)$", md, re.M)
        title = title_m.group(1).strip() if title_m else key
        html = _wrap_html(_md_to_html(md, doc_class), doc_class=doc_class, title=title)
        (PDF_DIR / f"{out.stem}.html").write_text(html, encoding="utf-8")
    build_pdf_from_md(src, out, doc_class)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Garden PDFs (PyMuPDF)")
    parser.add_argument(
        "target",
        nargs="?",
        choices=("all", "tripwire", "preview", "guide"),
        default="all",
    )
    parser.add_argument("--keep-html", action="store_true", help="Also write HTML preview")
    args = parser.parse_args()
    keys = list(SOURCES) if args.target == "all" else [args.target]
    for k in keys:
        out = build_one(k, keep_html=args.keep_html)
        print(f"OK {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
