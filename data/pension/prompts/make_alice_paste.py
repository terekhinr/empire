#!/usr/bin/env python3
"""Собрать один файл для Алисы: правила + одна статья."""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("pension_alice_one_paste.md")
DZEN = ROOT / "content" / "series_launch_2026" / "dzen"
OUT_DIR = Path(__file__).with_name("alice_ready")

MARKER_START = "<<<СТАТЬЯ"
MARKER_END = "СТАТЬЯ>>>"


def build(article: Path) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    art = article.read_text(encoding="utf-8").strip()
    # drop volume meta line from draft (Alice will recount)
    lines = [l for l in art.splitlines() if not l.startswith("Объём:")]
    art = "\n".join(lines).strip()
    if MARKER_START not in tpl or MARKER_END not in tpl:
        raise SystemExit("template markers missing")
    pre, rest = tpl.split(MARKER_START, 1)
    _, post = rest.split(MARKER_END, 1)
    return f"{pre}{MARKER_START}\n{art}\n{MARKER_END}{post}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Один paste-файл для Алисы")
    ap.add_argument(
        "which",
        nargs="?",
        default="all",
        help="00|01|02|03|04|all или путь к .md",
    )
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.which == "all":
        files = sorted(DZEN.glob("0*.md"))
    elif args.which in {"00", "01", "02", "03", "04"}:
        files = list(DZEN.glob(f"{args.which}_*.md"))
    else:
        files = [Path(args.which)]

    if not files:
        raise SystemExit("статья не найдена")

    for f in files:
        out = OUT_DIR / f"alice_{f.stem}.md"
        text = build(f)
        out.write_text(text, encoding="utf-8")
        print(f"{out}  chars={len(text)}  (~{len(text)//2} unicode-ish)")


if __name__ == "__main__":
    main()
