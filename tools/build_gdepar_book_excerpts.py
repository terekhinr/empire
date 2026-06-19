#!/usr/bin/env python3
"""
Импорт фрагментов из OCR-текста (FineReader) в data/gdepar_book_excerpts.json.

Формат разметки в .txt (удобно править руками после OCR):

### id: khoshev_dym_01
### rubric: pechi_banya
### author: Ю.М. Хошев
### work: «Дачные бани и печи» (2008)
### chapter: Глава 5. Дымоход
### tag: дымоход
quote:
Текст цитаты дословно, 2–8 предложений.
note:
Комментарий Михалыча — 2–4 предложения, без нравоучений.

Пример:
  ./venv/bin/python tools/build_gdepar_book_excerpts.py \\
    --from data/gdepar/incoming/khoshev.txt --merge

Авто-черновик из .rag.txt (грубая нарезка по абзацам):
  ./venv/bin/python tools/build_gdepar_book_excerpts.py \\
    --auto data/gdepar/Хошев*.rag.txt --rubric pechi_banya --limit 20 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "gdepar_book_excerpts.json"
CATALOG = ROOT / "data" / "gdepar_books_catalog.json"

_BLOCK = re.compile(
    r"###\s*id:\s*(?P<id>\S+)\s*\n"
    r"(?:###\s*rubric:\s*(?P<rubric>\S+)\s*\n)?"
    r"(?:###\s*author:\s*(?P<author>.+?)\s*\n)?"
    r"(?:###\s*work:\s*(?P<work>.+?)\s*\n)?"
    r"(?:###\s*chapter:\s*(?P<chapter>.+?)\s*\n)?"
    r"(?:###\s*tag:\s*(?P<tag>\S+)\s*\n)?"
    r"quote:\s*\n(?P<quote>.*?)(?:\nnote:\s*\n(?P<note>.*?))?(?=\n###\s*id:|\Z)",
    re.DOTALL | re.IGNORECASE,
)

_BANYA_KW = re.compile(
    r"(?i)(бан[яеи]|парил|печ[ьи]|каменк|дымоход|веник|пар[ау]|саун|купел|жар|пот)"
)


def _load_out() -> dict:
    if OUT.is_file():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"rubrics": {}, "entries": []}


def _slug(s: str) -> str:
    s = re.sub(r"[^\wа-яА-ЯёЁ]+", "_", s.lower(), flags=re.UNICODE)
    return s.strip("_")[:40] or "frag"


def parse_marked_blocks(text: str) -> list[dict]:
    out: list[dict] = []
    for m in _BLOCK.finditer(text):
        quote = (m.group("quote") or "").strip()
        if len(quote) < 80:
            continue
        entry = {
            "id": m.group("id").strip(),
            "rubric": (m.group("rubric") or "pechi_banya").strip(),
            "author": (m.group("author") or "").strip(),
            "work": (m.group("work") or "").strip(),
            "chapter": (m.group("chapter") or "").strip(),
            "quote": quote,
            "tag": (m.group("tag") or "книга").strip(),
        }
        note = (m.group("note") or "").strip()
        if note:
            entry["note"] = note
        out.append(entry)
    return out


def auto_chunks(
    text: str,
    *,
    rubric: str,
    author: str,
    work: str,
    limit: int,
) -> list[dict]:
    """Черновики из OCR: абзацы 200–900 символов с банной лексикой."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[dict] = []
    for i, p in enumerate(paras):
        p = re.sub(r"\s+", " ", p)
        if len(p) < 200 or len(p) > 900:
            continue
        if not _BANYA_KW.search(p):
            continue
        if p.count(" ") < 25:
            continue
        out.append(
            {
                "id": f"auto_{_slug(author)}_{i:04d}",
                "rubric": rubric,
                "author": author,
                "work": work,
                "chapter": "",
                "quote": p,
                "note": "",
                "tag": "черновик",
                "_draft": True,
            }
        )
        if len(out) >= limit:
            break
    return out


def merge_entries(data: dict, new_entries: list[dict], *, replace: bool) -> int:
    by_id = {e["id"]: e for e in data.get("entries", []) if e.get("id")}
    added = 0
    for e in new_entries:
        eid = e.get("id")
        if not eid:
            continue
        if eid in by_id and not replace:
            continue
        by_id[eid] = e
        added += 1
    data["entries"] = list(by_id.values())
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description="Импорт фрагментов книг → gdepar_book_excerpts.json")
    ap.add_argument("--from", dest="src", help="Размеченный .txt после FineReader")
    ap.add_argument("--auto", help="Сырой OCR/.rag.txt — авто-нарезка (черновики)")
    ap.add_argument("--rubric", default="pechi_banya", help="Ключ рубрики для --auto")
    ap.add_argument("--limit", type=int, default=15, help="Макс. фрагментов для --auto")
    ap.add_argument("--merge", action="store_true", help="Добавить к существующим id")
    ap.add_argument("--replace", action="store_true", help="Перезаписать совпадающие id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.src and not args.auto:
        ap.print_help()
        return 1

    new_entries: list[dict] = []
    if args.src:
        text = Path(args.src).read_text(encoding="utf-8")
        new_entries = parse_marked_blocks(text)
        print(f"Размеченных блоков: {len(new_entries)}")
    if args.auto:
        path = Path(args.auto)
        text = path.read_text(encoding="utf-8", errors="replace")
        author, work = "?", path.name
        if CATALOG.is_file():
            cat = json.loads(CATALOG.read_text(encoding="utf-8"))
            for b in cat.get("books", []):
                for sf in b.get("source_files", []):
                    if path.name in sf or sf.endswith(path.name):
                        author = b.get("author", author)
                        work = f"«{b.get('title', '')}» ({b.get('year', '')})"
                        args.rubric = b.get("rubric_key", args.rubric)
        chunks = auto_chunks(
            text, rubric=args.rubric, author=author, work=work, limit=args.limit
        )
        print(f"Авто-черновиков: {len(chunks)} (нужна ручная правка note:)")
        new_entries.extend(chunks)

    if not new_entries:
        print("Ничего не найдено.", file=sys.stderr)
        return 1

    if args.dry_run:
        for e in new_entries[:5]:
            print(f"— {e['id']}: {e['quote'][:120]}…")
        if len(new_entries) > 5:
            print(f"… и ещё {len(new_entries) - 5}")
        return 0

    data = _load_out()
    n = merge_entries(data, new_entries, replace=args.replace)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Сохранено в {OUT} (+{n}, всего {len(data['entries'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
