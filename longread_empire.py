"""Лонгриды pension → HTML для Empire (Дзен RSS, VK, TG)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LONG = ROOT / "data/pension/longreads"
PUB = LONG / "publish"
STATIC_LR = ROOT / "static/longreads"

SITE_BASE = __import__("os").getenv("EMPIRE_CANONICAL_SITE", "https://neverretire.ru").rstrip("/")

META = [
    ("00", "Пилот"),
    ("01", "Демография"),
    ("02", "Баллы"),
    ("03", "FIRE"),
    ("04", "Инфляция"),
]

IMG_PLACEHOLDER = re.compile(
    r"\*\[Вставьте картинку:\s*`?([^`\]]+?)`?\s*(?:—[^*]*)?\]\*",
    re.IGNORECASE,
)
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def longread_md_path(num: str, platform: str = "dzen") -> Path:
    return PUB / platform / f"{num}.md"


def graphics_subfolder(num: str) -> str:
    return num if num in ("01", "02") else ""


def _inline_md(text: str) -> str:
    text = LINK.sub(r'<a href="\2">\1</a>', text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    return text


def sync_longread_images_to_static(num: str) -> list[str]:
    """PNG → static/longreads/NN/ для URL на neverretire.ru. Возвращает публичные URL."""
    sub = graphics_subfolder(num)
    if not sub:
        return []
    src_png = LONG / "graphics" / sub / "png"
    if not src_png.is_dir():
        from tools.build_longread_graphics import main as gen_graphics

        gen_graphics()
        try:
            from tools.build_longread_preview import export_all_png

            export_all_png()
        except Exception:
            pass
    dst = STATIC_LR / sub
    dst.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for png in sorted(src_png.glob("*.png")):
        shutil.copy2(png, dst / png.name)
        urls.append(f"{SITE_BASE}/static/longreads/{sub}/{png.name}")
    return urls


def _image_url_from_placeholder(ref: str, num: str) -> str | None:
    name = Path(ref.strip().split()[0]).name
    stem = Path(name).stem
    sub = graphics_subfolder(num)
    if not sub:
        return None
    png = STATIC_LR / sub / f"{stem}.png"
    if png.is_file():
        return f"{SITE_BASE}/static/longreads/{sub}/{stem}.png"
    return f"{SITE_BASE}/static/longreads/{sub}/{stem}.png"


def md_to_html_body(md: str, num: str, *, sync_images: bool = True, include_h1: bool = False) -> str:
    """Конвертирует publish-md в HTML для PostDraft / RSS content:encoded."""
    if sync_images and graphics_subfolder(num):
        sync_longread_images_to_static(num)

    lines = md.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("# "):
            if include_h1:
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
                out.append('<table style="width:100%;border-collapse:collapse;margin:1em 0">')
                out.append(
                    "<thead><tr>"
                    + "".join(
                        f'<th style="border:1px solid #ddd;padding:8px">{_inline_md(c)}</th>'
                        for c in header
                    )
                    + "</tr></thead>"
                )
                out.append("<tbody>")
                for row in body_rows:
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    out.append(
                        "<tr>"
                        + "".join(
                            f'<td style="border:1px solid #ddd;padding:8px">{_inline_md(c)}</td>'
                            for c in cells
                        )
                        + "</tr>"
                    )
                out.append("</tbody></table>")
            continue

        m = IMG_PLACEHOLDER.search(line)
        if m:
            ref = m.group(1).strip()
            url = _image_url_from_placeholder(ref, num)
            if url:
                out.append(
                    f'<figure style="margin:1.5em 0;text-align:center">'
                    f'<img src="{url}" alt="" style="max-width:100%;height:auto" loading="lazy">'
                    f"</figure>"
                )
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
                items.append(
                    f"<li>{_inline_md(re.sub(r'^\\d+\\.\\s*', '', lines[i].strip()))}</li>"
                )
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        out.append(f"<p>{_inline_md(line.strip())}</p>")
        i += 1

    return "\n".join(out)


def load_longread_html(num: str, platform: str = "dzen") -> tuple[str, str, str]:
    """(title, html_body, raw_md) из publish/dzen|vk/NN.md"""
    path = longread_md_path(num, platform)
    md = path.read_text(encoding="utf-8")
    lines = md.strip().split("\n")
    title = lines[0].lstrip("# ").strip()
    body_start = 1
    if platform == "vk" and len(lines) > 2 and lines[1].strip() and not lines[1].startswith("#"):
        # заголовок + лид + --- + тело
        for j, ln in enumerate(lines[1:], 1):
            if ln.strip() == "---":
                body_start = j + 1
                break
    body_md = "\n".join(lines[body_start:])
    html_body = md_to_html_body(body_md, num, include_h1=False)
    return title, html_body, md


async def create_longread_draft(num: str, platform: str = "dzen", html_override: str | None = None) -> int:
    """Создаёт PostDraft (pending) для модерации в Око Саурона."""
    title, html_body, _md = load_longread_html(num, platform)
    body = html_override if html_override is not None else html_body
    cover = first_cover_image_path(num)
    topic = f"longread-{num}-{platform}|{title}"

    from main import PostDraft, async_session, init_db

    await init_db()
    async with async_session() as session:
        draft = PostDraft(
            persona_key="pension",
            text_content=body,
            image_prompt=f"longread-{num}",
            image_path=cover,
            topic_raw=topic[:500],
            decision="pending",
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return int(draft.id)


def vk_plain_from_html(html: str) -> str:
    from empire_publish import _strip_html_for_vk

    return _strip_html_for_vk(html)


def dzen_rss_snippet(title: str, html_body: str, *, draft_id: int = 0) -> str:
    """Как попадёт в content:encoded RSS (без CDATA-обёртки)."""
    import html as html_lib

    from rss_maker import _dzen_body_html, _article_link

    class _P:
        persona_key = "pension"
        id = draft_id or 999

    link = _article_link(_P())
    return _dzen_body_html(title, html_body, link=link, already_html=True)


def first_cover_image_path(num: str) -> str | None:
    sub = graphics_subfolder(num)
    if not sub:
        return None
    sync_longread_images_to_static(num)
    png_dir = STATIC_LR / sub
    first = sorted(png_dir.glob("*.png")) if png_dir.is_dir() else []
    if first:
        return str(first[0].relative_to(ROOT)).replace("\\", "/")
    return None
