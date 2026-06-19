"""Markdown (Obsidian) → Telegram HTML: ссылки, цитаты, wikilinks."""

from __future__ import annotations

import html as html_std
import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_ANGLE_LINK = re.compile(r"<(https?://[^>\s]+)>")
_BARE_URL = re.compile(
    r'(?<![\w/"\'=])(https?://[^\s<>\[\]()]+(?:[^\s<>\[\]().,;:!?\'"\]]*[^\s<>\[\]().,;:!?\'"\]])?)'
)
_CALLOUT_PREFIX = re.compile(r"^\[!([^\]]+)\]\s*")
_IMG_WIKILINK = re.compile(r"!\[\[[^\]]+\]\]")
_STRIKE = re.compile(r"~~(.+?)~~")


def normalize_markdown_emphasis(text: str) -> str:
    """***жирный+курсив*** → **жирный** (Telegram не любит вложенный b/i)."""
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"**\1**", text)
    text = re.sub(r"___(.+?)___", r"__\1__", text)
    return text


def md_links_to_telegram_html(text: str) -> str:
    """[текст](https://...) → <a href> для Telegram HTML."""

    def repl(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        return (
            f'<a href="{html_std.escape(url, quote=True)}">'
            f"{html_std.escape(label)}</a>"
        )

    return _MD_LINK.sub(repl, text)


def md_wikilinks_to_telegram_html(text: str) -> str:
    """[[url]] / [[url|label]] / [[note|label]] → ссылка или текст."""

    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        if "|" in inner:
            target, label = inner.rsplit("|", 1)
            label = label.strip()
        else:
            target = inner
            label = target.split("#", 1)[0].strip()
        target = target.strip()
        if re.match(r"^https?://", target, re.IGNORECASE):
            return (
                f'<a href="{html_std.escape(target, quote=True)}">'
                f"{html_std.escape(label)}</a>"
            )
        return html_std.escape(label)

    return _WIKILINK.sub(repl, text)


def md_angle_links_to_telegram_html(text: str) -> str:
    """<https://...> → кликабельная ссылка."""

    def repl(m: re.Match) -> str:
        url = m.group(1)
        return (
            f'<a href="{html_std.escape(url, quote=True)}">'
            f"{html_std.escape(url)}</a>"
        )

    return _ANGLE_LINK.sub(repl, text)


def md_bare_urls_to_telegram_html(text: str) -> str:
    """Голые https:// в тексте (не внутри уже готового href)."""

    def repl(m: re.Match) -> str:
        url = m.group(1)
        return (
            f'<a href="{html_std.escape(url, quote=True)}">'
            f"{html_std.escape(url)}</a>"
        )

    return _BARE_URL.sub(repl, text)


def strip_obsidian_embeds(text: str) -> str:
    """Убирает ![[картинка]] — для TG используйте поле image: в frontmatter."""
    return _IMG_WIKILINK.sub("", text)


def inline_markdown_to_telegram_html(text: str) -> str:
    """Ссылки и акценты внутри одного абзаца (цитата Obsidian)."""
    t = strip_obsidian_embeds(text)
    t = md_wikilinks_to_telegram_html(t)
    t = md_angle_links_to_telegram_html(t)
    t = md_links_to_telegram_html(t)
    t = normalize_markdown_emphasis(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = _STRIKE.sub(r"<s>\1</s>", t)
    t = md_bare_urls_to_telegram_html(t)
    return t


def md_blockquotes_to_telegram_html(text: str) -> str:
    """Строки с префиксом > → <blockquote> (как в Obsidian)."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith(">"):
            block: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                s = lines[i].strip()
                if s.startswith(">"):
                    s = s[1:].strip()
                s = _CALLOUT_PREFIX.sub("", s)
                block.append(s)
                i += 1
            inner = "\n".join(block).strip()
            if inner:
                out.append(f"<blockquote>{inline_markdown_to_telegram_html(inner)}</blockquote>")
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


_TABLE_SEP = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")


def _strip_cell_markdown(cell: str) -> str:
    c = cell.strip()
    c = re.sub(r"\*\*(.+?)\*\*", r"\1", c)
    c = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", c)
    return c.strip()


def _split_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [_strip_cell_markdown(c) for c in s.split("|")]


def _markdown_table_to_mobile_blocks(header: list[str], rows: list[list[str]]) -> str:
    """Markdown-таблица → карточки (читаемо на мобильном TG; <pre> с кириллицей плывёт)."""
    lines: list[str] = []
    for row in rows:
        cells = row + [""] * max(0, len(header) - len(row))
        num = cells[0].rstrip(".")
        name = cells[1] if len(cells) > 1 else ""
        stats = (cells[2:5] + ["", "", ""])[:3]
        lines.append(f"**{num}.** **{name}**")
        lines.append(
            f"мест **{stats[0]}** · заявл. **{stats[1]}** · зач. **{stats[2]}**"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def md_tables_to_telegram_pre(text: str) -> str:
    """Markdown-таблица → мобильные блоки (Telegram HTML не умеет <table>)."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            header = _split_table_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(_split_table_row(lines[i]))
                i += 1
            if rows:
                out.append(_markdown_table_to_mobile_blocks(header, rows))
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def enrich_obsidian_markdown(text: str) -> str:
    """Obsidian-специфика до общего fix_html_safety."""
    text = strip_obsidian_embeds(text)
    text = md_tables_to_telegram_pre(text)
    text = md_wikilinks_to_telegram_html(text)
    text = md_blockquotes_to_telegram_html(text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    return text
