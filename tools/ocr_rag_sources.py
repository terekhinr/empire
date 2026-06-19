#!/usr/bin/env python3
"""
OCR для сканов без текстового слоя (djvu, «пустые» PDF).

Пишет рядом с файлом: `<имя>.djvu.rag.txt` (или перезаписывает пустой .rag.txt).
Дальше: `./venv/bin/python tools/build_rag.py --persona <имя> --force`

Требования:
  apt install djvulibre-bin tesseract-ocr tesseract-ocr-rus
  pip: pytesseract pillow  (уже в venv Empire)

Примеры:
  ./venv/bin/python tools/ocr_rag_sources.py --persona gdepar --persona stern
  ./venv/bin/python tools/ocr_rag_sources.py --file "data/stern/Мохан…djvu"
  ./venv/bin/python tools/ocr_rag_sources.py --persona gdepar --max-pages 5   # проба
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OCR_CACHE = REPO / "data" / "ocr_cache" / "djvu"
OCR_LANG = "rus+eng"
OCR_DPI_SCALE = 150  # ddjvu -scale=… (проценты, 100≈72dpi)
MIN_OUT_BYTES = 500
PERSONAS = ("garden", "gdepar", "stern", "lenin", "pension")

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None  # type: ignore
    Image = None  # type: ignore


def _ocr_ready() -> bool:
    if pytesseract is None or Image is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        subprocess.run(["djvused", "-help"], capture_output=True, check=False)
        return True
    except Exception:
        return False


def _djvu_page_count(path: Path) -> int:
    r = subprocess.run(
        ["djvused", str(path), "-e", "n"],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return 0
    try:
        return int((r.stdout or "").strip())
    except ValueError:
        return 0


def _render_page(djvu: Path, page: int, ppm_path: Path) -> bool:
    cmd = [
        "ddjvu",
        f"-page={page}",
        f"-scale={OCR_DPI_SCALE}",
        "-format=ppm",
        str(djvu),
        str(ppm_path),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)
        return ppm_path.is_file() and ppm_path.stat().st_size > 1000
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _ocr_image(ppm_path: Path) -> str:
    with Image.open(ppm_path) as img:
        return (pytesseract.image_to_string(img, lang=OCR_LANG) or "").strip()


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.name.encode("utf-8"))
    h.update(str(path.stat().st_mtime_ns).encode())
    h.update(str(path.stat().st_size).encode())
    return h.hexdigest()[:24]


def _rag_txt_path(src: Path) -> Path:
    return src.with_suffix(src.suffix + ".rag.txt")


def needs_ocr(src: Path, *, force: bool) -> bool:
    if src.suffix.lower() != ".djvu":
        return False
    out = _rag_txt_path(src)
    if force:
        return True
    if not out.is_file():
        return True
    return out.stat().st_size < MIN_OUT_BYTES


def ocr_djvu(
    src: Path,
    *,
    max_pages: int | None = None,
    force: bool = False,
) -> Path | None:
    out = _rag_txt_path(src)
    if not needs_ocr(src, force=force):
        print(f"  skip (text ok) {out.name}")
        return out

    n_pages = _djvu_page_count(src)
    if n_pages < 1:
        print(f"  FAIL page count: {src.name}", file=sys.stderr)
        return None

    limit = min(n_pages, max_pages) if max_pages else n_pages
    cache_dir = OCR_CACHE / _file_digest(src)
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / "meta.json"

    pages_done: dict[str, str] = {}
    if meta_path.is_file() and not force:
        try:
            pages_done = {
                str(p["page"]): p["text"]
                for p in json.loads(meta_path.read_text(encoding="utf-8")).get("pages", [])
                if p.get("text")
            }
        except Exception:
            pages_done = {}

    print(f"  OCR {src.name}: {limit}/{n_pages} стр., scale={OCR_DPI_SCALE}, lang={OCR_LANG}")

    with tempfile.TemporaryDirectory(prefix="empire_ocr_") as tmp:
        tmp_p = Path(tmp)
        for page in range(1, limit + 1):
            key = str(page)
            if key in pages_done:
                continue
            page_cache = cache_dir / f"p{page:04d}.txt"
            if page_cache.is_file() and not force:
                text = page_cache.read_text(encoding="utf-8").strip()
            else:
                ppm = tmp_p / f"p{page}.ppm"
                if not _render_page(src, page, ppm):
                    print(f"    render fail page {page}", file=sys.stderr)
                    text = ""
                else:
                    text = _ocr_image(ppm)
                    page_cache.write_text(text, encoding="utf-8")
            if text:
                pages_done[key] = text
            if page % 20 == 0 or page == limit:
                meta_path.write_text(
                    json.dumps(
                        {
                            "source": str(src),
                            "pages": [{"page": int(k), "text": v} for k, v in sorted(pages_done.items(), key=lambda x: int(x[0]))],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                print(f"    … {page}/{limit} стр., символов: {sum(len(t) for t in pages_done.values())}")

    ordered = [pages_done[str(i)] for i in range(1, limit + 1) if str(i) in pages_done]
    body = "\n\n".join(ordered)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) < MIN_OUT_BYTES:
        print(f"  WARN мало текста ({len(body)} симв.): {src.name}", file=sys.stderr)
        return None

    out.write_text(body, encoding="utf-8")
    print(f"  ok   → {out.name} ({len(body) // 1024} KiB, {len(ordered)} стр.)")
    return out


def iter_djvu(personas: list[str], explicit: list[Path]) -> list[Path]:
    if explicit:
        return sorted(explicit)
    found: list[Path] = []
    for persona in personas:
        for root in (REPO / "data" / persona, REPO / "kb_sources" / persona):
            if root.is_dir():
                found.extend(root.rglob("*.djvu"))
                found.extend(root.rglob("*.DJVU"))
    return sorted(set(found))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", action="append", default=[])
    ap.add_argument("--file", action="append", default=[], type=Path, help="конкретный .djvu")
    ap.add_argument("--force", action="store_true", help="пере-OCR даже если .rag.txt не пустой")
    ap.add_argument("--max-pages", type=int, default=0, help="лимит страниц (0 = все)")
    ap.add_argument("--all-empty", action="store_true", help="только файлы с пустым .rag.txt")
    args = ap.parse_args()

    if not _ocr_ready():
        print("Нужны: djvulibre-bin, tesseract (rus+eng), pytesseract, Pillow", file=sys.stderr)
        sys.exit(1)

    personas = args.persona or list(PERSONAS)
    explicit = [Path(p) if p.is_absolute() else REPO / p for p in args.file]
    files = iter_djvu(personas, explicit)
    if args.all_empty:
        files = [f for f in files if needs_ocr(f, force=False)]

    max_pages = args.max_pages if args.max_pages > 0 else None
    ok = 0
    for src in files:
        if src.suffix.lower() != ".djvu":
            continue
        if args.all_empty and not needs_ocr(src, force=False):
            continue
        print(f"== {src.relative_to(REPO)} ==")
        if ocr_djvu(src, max_pages=max_pages, force=args.force):
            ok += 1

    print(f"\nГотово: {ok} файл(ов). Дальше: tools/build_rag.py --force --persona …")


if __name__ == "__main__":
    main()
