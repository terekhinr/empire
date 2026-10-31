"""Разбор .md/.txt постов и матриц (CSV, markdown-таблица, простой список)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from publisher.catalog import parse_weekday, resolve_project_id

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
_TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def parse_post_file(
    filename: str,
    text: str,
    *,
    default_project: str | None = None,
) -> dict[str, Any]:
    """Один файл = один пост. Frontmatter необязателен."""
    name = (filename or "post.md").strip() or "post.md"
    body_src = text.replace("\r\n", "\n").replace("\r", "\n")
    meta: dict[str, str] = {}
    m = _FRONTMATTER_RE.match(body_src)
    if m:
        meta = _parse_simple_yaml(m.group(1))
        body_src = m.group(2)

    title = (meta.get("title") or meta.get("заголовок") or "").strip()
    body = body_src.strip()
    if not title:
        title, body = _title_from_body(body, name)

    project = resolve_project_id(
        meta.get("project") or meta.get("persona") or meta.get("канал") or "",
        default_project,
    )
    scheduled = (meta.get("scheduled") or meta.get("когда") or "").strip() or None
    slot_time = (meta.get("slot") or meta.get("слот") or meta.get("time") or "").strip() or None
    if slot_time and not _TIME_RE.search(slot_time):
        slot_time = None
    weekday = parse_weekday(meta.get("weekday") or meta.get("день") or "")

    return {
        "title": title[:200],
        "body": body,
        "project_id": project,
        "scheduled_at": scheduled,
        "slot_time": slot_time,
        "weekday": weekday,
        "source_filename": name,
    }


def _title_from_body(body: str, filename: str) -> tuple[str, str]:
    lines = body.split("\n")
    if lines and lines[0].lstrip().startswith("#"):
        title = lines[0].lstrip("#").strip()
        rest = "\n".join(lines[1:]).strip()
        return title or _title_from_filename(filename), rest
    if lines and lines[0].strip():
        first = lines[0].strip()
        if len(first) <= 80 and (len(lines) == 1 or not lines[1].strip() or first.endswith((".", "!", "?", "…"))):
            # Короткая первая строка — заголовок, если дальше пустая строка
            if len(lines) > 1 and not lines[1].strip():
                return first, "\n".join(lines[2:]).strip()
    return _title_from_filename(filename), body


def _title_from_filename(filename: str) -> str:
    stem = filename.rsplit("/", 1)[-1]
    stem = re.sub(r"\.(md|txt|markdown)$", "", stem, flags=re.I)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Без названия"


def _parse_simple_yaml(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().strip("\"'")
        val = v.strip().strip("\"'")
        if key:
            out[key] = val
    return out


def parse_matrix_text(
    text: str,
    *,
    default_project: str | None = None,
) -> list[dict[str, Any]]:
    """CSV, TSV, markdown-таблица или строки «Пн 11:00 | заголовок»."""
    src = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not src:
        return []
    if src.lstrip().startswith("|") or _looks_like_md_table(src):
        rows = _parse_md_table(src)
        return [_row_to_entry(r, default_project) for r in rows if r]
    if "," in src.split("\n", 1)[0] or ";" in src.split("\n", 1)[0] or "\t" in src.split("\n", 1)[0]:
        rows = _parse_csv(src)
        return [_row_to_entry(r, default_project) for r in rows if r]
    return _parse_plain_lines(src, default_project)


def _looks_like_md_table(src: str) -> bool:
    lines = [ln for ln in src.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    return "|" in lines[0] and _is_md_sep_row(lines[1])


def _is_md_sep_row(line: str) -> bool:
    cells = _split_md_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells)


def _parse_md_table(src: str) -> list[dict[str, str]]:
    lines = [ln.strip() for ln in src.splitlines() if ln.strip()]
    if not lines:
        return []
    header_cells = _split_md_row(lines[0])
    body_lines = lines[1:]
    if body_lines and _is_md_sep_row(body_lines[0]):
        body_lines = body_lines[1:]
    keys = [_norm_header(h) for h in header_cells]
    rows: list[dict[str, str]] = []
    for ln in body_lines:
        if _is_md_sep_row(ln):
            continue
        cells = _split_md_row(ln)
        row = {keys[i]: (cells[i] if i < len(cells) else "") for i in range(len(keys))}
        rows.append(row)
    return rows


def _split_md_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _parse_csv(src: str) -> list[dict[str, str]]:
    sample = src.split("\n", 1)[0]
    if sample.count(";") > sample.count(",") and sample.count(";") >= sample.count("\t"):
        delimiter = ";"
    elif "\t" in sample:
        delimiter = "\t"
    else:
        delimiter = ","
    reader = csv.reader(io.StringIO(src), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        return []
    keys = [_norm_header(h) for h in header]
    n = len(keys)
    rows: list[dict[str, str]] = []
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue
        if len(cells) > n >= 1:
            cells = cells[: n - 1] + [delimiter.join(cells[n - 1 :])]
        row = {keys[i]: (cells[i].strip() if i < len(cells) else "") for i in range(n)}
        rows.append(row)
    return rows


def _norm_header(h: str) -> str:
    s = (h or "").strip().lower()
    aliases = {
        "project": "project",
        "канал": "project",
        "персона": "project",
        "persona": "project",
        "куда": "project",
        "weekday": "weekday",
        "день": "weekday",
        "dow": "weekday",
        "time": "time",
        "слот": "time",
        "время": "time",
        "title": "title",
        "заголовок": "title",
        "тема": "title",
        "body": "body",
        "текст": "body",
        "контент": "body",
        "пост": "body",
        "file": "file",
        "файл": "file",
    }
    return aliases.get(s, s)


def _row_to_entry(row: dict[str, str], default_project: str | None) -> dict[str, Any] | None:
    if not row:
        return None
    body = (row.get("body") or "").strip()
    title = (row.get("title") or "").strip()
    file_name = (row.get("file") or "").strip()
    if not body and not title and not file_name:
        return None
    if not title:
        title = (body.split("\n", 1)[0][:80] if body else file_name) or "Без названия"
    time_s = (row.get("time") or "").strip()
    tm = _TIME_RE.search(time_s) if time_s else None
    slot_time = f"{int(tm.group(1)):02d}:{tm.group(2)}" if tm else (time_s or None)
    return {
        "title": title[:200],
        "body": body,
        "project_id": resolve_project_id(row.get("project") or "", default_project),
        "weekday": parse_weekday(row.get("weekday") or ""),
        "slot_time": slot_time,
        "source_filename": file_name or None,
        "scheduled_at": None,
    }


def _parse_plain_lines(src: str, default_project: str | None) -> list[dict[str, Any]]:
    """Блоки, разделённые ---, или строки «Пн 11:00 Заголовок»."""
    chunks = re.split(r"\n---+\n", src)
    if len(chunks) == 1 and "\n\n" in src and not _TIME_RE.search(src.split("\n", 1)[0]):
        chunks = [src]
    out: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        first, _, rest = chunk.partition("\n")
        wd = None
        slot_time = None
        title = first.strip()
        tm = _TIME_RE.search(first)
        if tm:
            slot_time = f"{int(tm.group(1)):02d}:{tm.group(2)}"
            head = (first[: tm.start()] + first[tm.end() :]).strip(" |-—–")
            wd = parse_weekday(head.split()[0]) if head.split() else None
            title = " ".join(head.split()[1:]) if wd is not None and len(head.split()) > 1 else head
        body = rest.strip()
        if not title and not body:
            continue
        if not title:
            title, body = _title_from_body(body, "matrix")
        out.append(
            {
                "title": (title or "Без названия")[:200],
                "body": body,
                "project_id": default_project,
                "weekday": wd,
                "slot_time": slot_time,
                "source_filename": None,
                "scheduled_at": None,
            }
        )
    return out
