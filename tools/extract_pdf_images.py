#!/usr/bin/env python3
"""Извлечение растровых иллюстраций из PDF в media/<persona>/pool/.

Цель — собрать «правильные» картинки упражнений из книг Цацулина/МакГилла
и подкладывать их под посты Штерна вместо генерации в fal.

Пример:
  ./venv/bin/python tools/extract_pdf_images.py \
      --persona stern \
      --src-dir data/stern \
      --min-side 380 \
      --max-per-pdf 80
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageStat


def _quality_ok(pil: Image.Image, min_mean: float, max_mean: float, min_std: float) -> bool:
    """Отбрасываем «обложечные» однотонные и чёрные растры."""
    try:
        thumb = pil.copy()
        thumb.thumbnail((400, 400))
        st = ImageStat.Stat(thumb.convert("RGB"))
        avg_m = sum(st.mean) / 3.0
        avg_s = sum(st.stddev) / 3.0
        if avg_m < min_mean or avg_m > max_mean:
            return False
        if avg_s < min_std:
            return False
        return True
    except Exception:
        return False


def extract(
    pdf_path: Path,
    out_dir: Path,
    min_side: int,
    max_per_pdf: int,
    quality: int,
    aspect_min: float = 0.55,
    aspect_max: float = 1.8,
    max_pixels: int = 6_000_000,
    skip_first_pages: int = 4,
    min_mean: float = 42.0,
    max_mean: float = 245.0,
    min_std: float = 14.0,
) -> int:
    saved = 0
    seen_hashes: set[str] = set()
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  SKIP open {pdf_path.name}: {e}", file=sys.stderr)
        return 0

    base = pdf_path.stem
    for pno in range(len(doc)):
        if saved >= max_per_pdf:
            break
        if pno < skip_first_pages:
            continue
        try:
            page = doc[pno]
            images = page.get_images(full=True)
        except Exception:
            continue
        for ix, img in enumerate(images):
            if saved >= max_per_pdf:
                break
            xref = img[0]
            try:
                base_img = doc.extract_image(xref)
            except Exception:
                continue
            data = base_img.get("image")
            if not data:
                continue
            try:
                pil = Image.open(BytesIO(data)).convert("RGB")
            except Exception:
                continue
            w, h = pil.size
            if min(w, h) < min_side:
                continue
            ar = w / h if h else 0
            if ar < aspect_min or ar > aspect_max:
                # отбрасываем книжные полосы / полностраничные сканы (1:1.4+) и узкие шапки
                continue
            if w * h > max_pixels:
                # очень крупные сканы страниц
                continue
            if not _quality_ok(pil, min_mean, max_mean, min_std):
                continue
            digest = hashlib.md5(data).hexdigest()[:10]
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            out = out_dir / f"{base}_p{pno+1:04d}_{ix}_{digest}.jpg"
            try:
                pil.save(out, "JPEG", quality=quality, optimize=True)
                saved += 1
            except Exception as e:
                print(f"  fail save {out.name}: {e}", file=sys.stderr)
    doc.close()
    return saved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True, help="например stern")
    ap.add_argument(
        "--src-dir",
        action="append",
        default=[],
        help="папка с PDF (можно несколько раз)",
    )
    ap.add_argument("--out-dir", default="", help="по умолчанию media/<persona>/pool")
    ap.add_argument("--min-side", type=int, default=380, help="мин. меньшая сторона картинки")
    ap.add_argument("--max-per-pdf", type=int, default=80)
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--skip-first-pages", type=int, default=4)
    ap.add_argument("--min-mean", type=float, default=42.0)
    ap.add_argument("--max-mean", type=float, default=245.0)
    ap.add_argument("--min-std", type=float, default=14.0)
    ap.add_argument(
        "--include",
        action="append",
        default=[],
        help="индексировать только PDF, имя которых содержит подстроку (можно несколько)",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    out = Path(args.out_dir) if args.out_dir else repo / "media" / args.persona / "pool"
    out.mkdir(parents=True, exist_ok=True)

    srcs = [Path(p) for p in args.src_dir] if args.src_dir else [repo / "data" / args.persona]
    total = 0
    for srcdir in srcs:
        if not srcdir.is_dir():
            print(f"  WARN: нет каталога {srcdir}", file=sys.stderr)
            continue
        for pdf in sorted(srcdir.glob("*.pdf")):
            if args.include and not any(s.lower() in pdf.name.lower() for s in args.include):
                continue
            n = extract(
                pdf, out, args.min_side, args.max_per_pdf, args.quality,
                skip_first_pages=args.skip_first_pages,
                min_mean=args.min_mean, max_mean=args.max_mean, min_std=args.min_std,
            )
            print(f"  {pdf.name}: +{n}")
            total += n
    print(f"OK → {out}  (всего сохранено: {total})")


if __name__ == "__main__":
    main()
