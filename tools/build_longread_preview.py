#!/usr/bin/env python3
"""HTML-превью лонгридов Дзен/VK + PNG из SVG для загрузки в редактор."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG = ROOT / "data/pension/longreads"
PUB = LONG / "publish"
PREVIEW = PUB / "preview"
GRAPHICS = LONG / "graphics"

# (publish_id, platform, md stem, graphics subfolder or None)
JOBS = [
    ("01", "dzen", "01", "01"),
    ("02", "dzen", "02", "02"),
    ("01", "vk", "01", "01"),
    ("02", "vk", "02", "02"),
]

IMG_PLACEHOLDER = re.compile(
    r"\*\[Вставьте картинку:\s*`?([^`\]]+?)`?\s*(?:—[^*]*)?\]\*",
    re.IGNORECASE,
)
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def _ensure_png(svg: Path, png: Path) -> None:
    png.parent.mkdir(parents=True, exist_ok=True)
    if png.exists() and png.stat().st_mtime >= svg.stat().st_mtime:
        return
    try:
        import cairosvg

        cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1200)
    except Exception as exc:
        print(f"  warn PNG {png.name}: {exc}", file=sys.stderr)


def export_all_png() -> None:
    for sub in ("01", "02"):
        src_dir = GRAPHICS / sub
        dst_dir = src_dir / "png"
        for svg in sorted(src_dir.glob("*.svg")):
            _ensure_png(svg, dst_dir / f"{svg.stem}.png")
            print(f"  png {sub}/{svg.stem}.png")


def _inline_md(text: str) -> str:
    text = LINK.sub(r'<a href="\2">\1</a>', text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    return text


def _md_to_html(md: str, graphics_sub: str | None) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            out.append(f"<h1>{_inline_md(line[2:].strip())}</h1>")
            i += 1
            continue
        if line.startswith("## "):
            out.append(f"<h2>{_inline_md(line[3:].strip())}</h2>")
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) >= 2:
                header = [c.strip() for c in rows[0].strip("|").split("|")]
                body_rows = rows[2:] if re.match(r"^\|[\s\-:|]+\|$", rows[1].strip()) else rows[1:]
                out.append('<table class="data">')
                out.append("<thead><tr>" + "".join(f"<th>{_inline_md(c)}</th>" for c in header) + "</tr></thead>")
                out.append("<tbody>")
                for row in body_rows:
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    out.append("<tr>" + "".join(f"<td>{_inline_md(c)}</td>" for c in cells) + "</tr>")
                out.append("</tbody></table>")
            continue
        m = IMG_PLACEHOLDER.search(line)
        if m:
            ref = m.group(1).strip().split()[0]
            name = Path(ref).name
            stem = Path(name).stem
            if graphics_sub:
                png_rel = f"../../graphics/{graphics_sub}/png/{stem}.png"
                svg_rel = f"../../graphics/{graphics_sub}/{name}" if name.endswith(".svg") else None
                out.append('<figure class="infographic">')
                out.append(f'<img src="{png_rel}" alt="{stem}" loading="lazy">')
                if svg_rel:
                    out.append(f'<figcaption>PNG для загрузки в Дзен/VK · исходник: <code>{svg_rel}</code></figcaption>')
                out.append("</figure>")
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{_inline_md(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s", line.strip()):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                items.append(f"<li>{_inline_md(re.sub(r'^\\d+\\.\\s*', '', lines[i].strip()))}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        out.append(f"<p>{_inline_md(line.strip())}</p>")
        i += 1
    return "\n".join(out)


CSS = """
:root { font-family: Georgia, 'Times New Roman', serif; line-height: 1.55; color: #1a1a2e; background: #fafafa; }
body { max-width: 720px; margin: 0 auto; padding: 24px 20px 48px; background: #fff; box-shadow: 0 0 24px #0001; }
.banner { background: #1a1a2e; color: #fff; padding: 12px 16px; margin: -24px -20px 24px; font-family: system-ui, sans-serif; font-size: 14px; }
.banner a { color: #93c5fd; }
h1 { font-size: 1.65rem; line-height: 1.25; margin-top: 0; }
h2 { font-size: 1.2rem; margin-top: 1.6em; border-bottom: 2px solid #e85d04; padding-bottom: 4px; }
table.data { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.92rem; }
table.data th, table.data td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; }
table.data th { background: #f1f5f9; }
figure.infographic { margin: 1.5em 0; text-align: center; }
figure.infographic img { max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 6px; }
figcaption { font-size: 0.8rem; color: #666; margin-top: 8px; font-family: system-ui, sans-serif; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 2em 0; }
a { color: #2563eb; }
code { font-size: 0.85em; background: #f1f5f9; padding: 2px 5px; border-radius: 3px; }
"""


def _page(title: str, body_html: str, meta: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · превью</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="banner">Превью для проверки перед публикацией · {meta} · <a href="index.html">← все выпуски</a></div>
  {body_html}
</body>
</html>"""


def build_previews() -> None:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    links: list[str] = []
    for pid, platform, stem, gsub in JOBS:
        md_path = PUB / platform / f"{stem}.md"
        md = md_path.read_text(encoding="utf-8")
        # skip footer for cleaner preview (optional - keep all)
        body = _md_to_html(md, gsub)
        title_line = md.strip().split("\n", 1)[0].lstrip("# ").strip()
        fname = f"{platform}-{stem}.html"
        html = _page(title_line, body, f"{platform.upper()} · выпуск {stem}")
        (PREVIEW / fname).write_text(html, encoding="utf-8")
        links.append((fname, f"{platform.upper()} {stem}: {title_line[:60]}…"))
        print(f"  html {fname}")

    # gallery
    gallery_items = []
    for sub in ("01", "02"):
        for png in sorted((GRAPHICS / sub / "png").glob("*.png")):
            rel = f"../../graphics/{sub}/png/{png.name}"
            gallery_items.append(
                f'<figure><img src="{rel}" alt="{png.stem}"><figcaption>{sub}/{png.name}</figcaption></figure>'
            )
    gallery = "\n".join(gallery_items)
    (PREVIEW / "graphics.html").write_text(
        _page("Инфографика 01–02", f"<h1>Инфографика выпусков 01–02</h1>\n<div class=\"gallery\">{gallery}</div>", "галерея")
        + "<style>.gallery{display:grid;gap:24px;}</style>",
        encoding="utf-8",
    )

    index_body = "<h1>Лонгриды · превью перед публикацией</h1>"
    index_body += "<p><strong>Для Дзен и VK HTML не нужен</strong> — в редактор вставляете текст из <code>publish/dzen/*.md</code>, картинки загружаете из <code>graphics/NN/png/</code>. HTML здесь только чтобы <em>посмотреть</em>, как всё сложится.</p>"
    index_body += "<ul>"
    for fname, label in links:
        index_body += f'<li><a href="{fname}">{label}</a></li>'
    index_body += '<li><a href="graphics.html">Только инфографика (01 + 02)</a></li>'
    index_body += "</ul>"
    index_body += "<p>PNG: <code>python3 tools/build_longread_preview.py</code></p>"
    (PREVIEW / "index.html").write_text(_page("Индекс превью", index_body, "index"), encoding="utf-8")
    print(f"  index → {PREVIEW / 'index.html'}")


def main() -> None:
    print("PNG из SVG…")
    export_all_png()
    print("HTML превью…")
    build_previews()


if __name__ == "__main__":
    main()
