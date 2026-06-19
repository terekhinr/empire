#!/usr/bin/env python3
"""TickTick backup CSV → Obsidian Tasks markdown (append to inbox.md)."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None  # type: ignore


PRIORITY_MAP = {5: "⏫", 3: "🔼", 1: "🔽"}


def parse_ticktick_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if date_parser:
        try:
            dt = date_parser.parse(raw)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    return m.group(1) if m else None


def repeat_to_obsidian(rrule: str) -> str:
    r = (rrule or "").upper()
    if not r or "FREQ=" not in r:
        return ""
    if "DAILY" in r:
        return " 🔁 every day"
    if "WEEKLY" in r:
        return " 🔁 every week"
    if "MONTHLY" in r:
        return " 🔁 every month"
    if "YEARLY" in r:
        return " 🔁 every year"
    return f" 🔁 {rrule}"


def tags_field(raw: str, list_name: str) -> str:
    parts: list[str] = []
    if list_name and list_name.lower() not in ("inbox", "tasks", "notes"):
        slug = re.sub(r"[^\w\-]+", "_", list_name.strip())[:40]
        if slug:
            parts.append(f"#{slug}")
    for t in (raw or "").replace(",", " ").split():
        t = t.strip()
        if t:
            parts.append(f"#{t}" if not t.startswith("#") else t)
    return (" " + " ".join(parts)) if parts else ""


def row_to_task(row: dict[str, str]) -> str | None:
    status = (row.get("Status") or row.get("status") or "0").strip()
    if status not in ("0", ""):
        return None

    title = (row.get("Title") or row.get("title") or "").strip()
    if not title:
        return None

    list_name = (row.get("List Name") or row.get("list name") or "").strip()
    due = parse_ticktick_date(row.get("Due Date") or row.get("due date") or "")
    prio_raw = (row.get("Priority") or "0").strip()
    try:
        prio = PRIORITY_MAP.get(int(prio_raw), "")
    except ValueError:
        prio = ""

    line = f"- [ ] {title}"
    if due:
        line += f" 📅 {due}"
    if prio:
        line += f" {prio}"
    line += repeat_to_obsidian(row.get("Repeat") or row.get("repeat") or "")
    line += tags_field(row.get("Tags") or "", list_name)

    content = (row.get("Content") or "").strip()
    if content and len(content) < 200 and "\n" not in content:
        line += f" — {content}"
    return line


def read_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    # Skip TickTick header comments until CSV header row
    start = 0
    for i, line in enumerate(lines):
        if line.startswith('"Folder Name"') or line.startswith("Folder Name"):
            start = i
            break
    reader = csv.DictReader(lines[start:])
    return list(reader)


def main() -> int:
    ap = argparse.ArgumentParser(description="TickTick CSV → Obsidian Tasks")
    ap.add_argument("csv_path", type=Path, help="ticktick-backup.csv")
    ap.add_argument(
        "out_md",
        type=Path,
        nargs="?",
        help="inbox.md (default: append section to file)",
    )
    ap.add_argument(
        "--replace",
        action="store_true",
        help="Replace file content instead of append",
    )
    args = ap.parse_args()

    if not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1

    rows = read_csv(args.csv_path)
    tasks: list[str] = []
    for row in rows:
        t = row_to_task(row)
        if t:
            tasks.append(t)

    if not tasks:
        print("No active tasks (Status=0). Check CSV.", file=sys.stderr)
        return 2

    header = f"\n\n## Импорт TickTick ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    body = header + "\n".join(tasks) + "\n"

    out = args.out_md
    if out is None:
        print(body)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    if args.replace:
        out.write_text("# Inbox\n" + body, encoding="utf-8")
    else:
        prev = out.read_text(encoding="utf-8") if out.is_file() else "# Inbox\n"
        out.write_text(prev.rstrip() + body, encoding="utf-8")

    print(f"Wrote {len(tasks)} tasks -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
