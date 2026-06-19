#!/usr/bin/env python3
"""
Конвертация djvu / fb2 / epub → .txt для RAG (tools/build_rag.py индексирует .txt).

Требования на VPS:
  apt install djvulibre-bin pandoc

Пример:
  ./venv/bin/python tools/convert_rag_sources.py
  ./venv/bin/python tools/convert_rag_sources.py --persona gdepar
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PERSONAS = ("garden", "gdepar", "stern", "lenin", "pension")


def _run(cmd: list[str], *, timeout: int = 3600) -> bool:
    try:
        subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  FAIL {' '.join(cmd[:3])}…: {e}", file=sys.stderr)
        return False


def convert_file(src: Path) -> Path | None:
    out = src.with_suffix(src.suffix + ".rag.txt")
    if out.is_file() and out.stat().st_mtime >= src.stat().st_mtime:
        print(f"  skip (fresh) {out.name}")
        return out
    suf = src.suffix.lower()
    if suf == ".djvu":
        if not _run(["djvutxt", str(src), str(out)]):
            return None
    elif suf in (".fb2", ".epub"):
        if not _run(
            ["pandoc", str(src), "-t", "plain", "-o", str(out), "--wrap=none"],
            timeout=600,
        ):
            return None
    else:
        return None
    if out.is_file() and out.stat().st_size > 200:
        print(f"  ok   {src.name} → {out.name} ({out.stat().st_size // 1024} KiB)")
        return out
    print(f"  empty {out.name} — запустите: tools/ocr_rag_sources.py --file {src}", file=sys.stderr)
    return None


def iter_sources(persona: str) -> list[Path]:
    roots = [REPO / "data" / persona, REPO / "kb_sources" / persona]
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for ext in ("*.djvu", "*.DJVU", "*.fb2", "*.FB2", "*.epub", "*.EPUB"):
            found.extend(root.rglob(ext))
    return sorted(set(found))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", action="append", default=[], help="garden|gdepar|… (можно несколько)")
    args = ap.parse_args()
    personas = args.persona or list(PERSONAS)
    ok = 0
    for persona in personas:
        files = iter_sources(persona)
        if not files:
            continue
        print(f"== {persona}: {len(files)} file(s) ==")
        for src in files:
            if convert_file(src):
                ok += 1
    print(f"Done: {ok} converted text file(s). Run build_rag.py --force per persona.")


if __name__ == "__main__":
    main()
