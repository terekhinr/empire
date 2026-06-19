#!/usr/bin/env python3
"""Crop, deskew and order photographed document pages."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _paper_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 0, 110), (180, 90, 255))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def _largest_quad(contours: list, min_area_ratio: float, shape: tuple[int, int]) -> np.ndarray | None:
    h, w = shape
    img_area = h * w
    best: np.ndarray | None = None
    best_area = 0.0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < img_area * min_area_ratio:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best_area = area
            best = approx.reshape(4, 2).astype(np.float32)
    return best


def _warp_document(bgr: np.ndarray, quad: np.ndarray) -> np.ndarray:
    rect = _order_points(quad)
    tl, tr, br, bl = rect
    max_w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    max_h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    max_w, max_h = max(max_w, 80), max(max_h, 80)
    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype=np.float32,
    )
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(bgr, m, (max_w, max_h), flags=cv2.INTER_CUBIC)


def extract_document(bgr: np.ndarray) -> np.ndarray:
    mask = _paper_mask(bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bgr

    cnt = max(contours, key=cv2.contourArea)
    area_ratio = cv2.contourArea(cnt) / (bgr.shape[0] * bgr.shape[1])
    quad = _largest_quad(contours, min_area_ratio=0.06, shape=bgr.shape[:2])

    if area_ratio < 0.45 or quad is None:
        x, y, w, h = cv2.boundingRect(cnt)
        pad = max(4, int(min(w, h) * 0.012))
        return bgr[
            max(0, y - pad) : min(bgr.shape[0], y + h + pad),
            max(0, x - pad) : min(bgr.shape[1], x + w + pad),
        ]

    return _warp_document(bgr, quad)


def _osd_upright_conf(bgr: np.ndarray) -> float:
    pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    w, h = pil.size
    scale = 2000 / max(w, h)
    if scale > 1.05:
        pil = pil.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    try:
        osd = pytesseract.image_to_osd(pil, config="--psm 0")
        rotate = int(re.search(r"Rotate: (\d+)", osd).group(1))
        conf = float(re.search(r"Orientation confidence: ([\d.]+)", osd).group(1))
        if rotate == 0:
            return conf
        if rotate == 180:
            return conf * 0.25
        return 0.0
    except Exception:
        return 0.0


def _ocr_top_score(bgr: np.ndarray) -> int:
    h = bgr.shape[0]
    part = bgr[: max(80, h // 4)]
    rgb = cv2.cvtColor(part, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    w, th = pil.size
    scale = 1800 / max(w, th)
    if scale > 1.05:
        pil = pil.resize((int(w * scale), int(th * scale)), Image.Resampling.LANCZOS)
    try:
        text = pytesseract.image_to_string(pil, lang="rus+eng", config="--psm 6")
    except Exception:
        text = ""
    words = re.findall(r"[А-Яа-яЁё]{4,}", text)
    return sum(len(w) for w in words) + len(words) * 8


def _text_horizontal_score(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    row_var = float(np.var(bw.sum(axis=1)))
    col_var = float(np.var(bw.sum(axis=0)))
    return row_var / (col_var + 1e-6)


def _orientation_quality(bgr: np.ndarray) -> float:
    h, w = bgr.shape[:2]
    osd = _osd_upright_conf(bgr) * 20.0
    top = float(_ocr_top_score(bgr))
    horiz = min(_text_horizontal_score(bgr), 15.0)
    portrait = 4.0 if h >= w * 1.02 else 0.0
    return osd + top + horiz + portrait


def auto_orient(bgr: np.ndarray) -> np.ndarray:
    scored: list[tuple[float, int]] = []
    for k in range(4):
        scored.append((_orientation_quality(np.rot90(bgr, k)), k))
    scored.sort(reverse=True)
    best_score = scored[0][0]
    top_ks = [k for s, k in scored if s >= best_score - 0.05]
    if 1 in top_ks and 3 in top_ks:
        k = 3
    else:
        k = scored[0][1]
    return np.rot90(bgr, k)


def trim_paper(bgr: np.ndarray) -> np.ndarray:
    """Mild edge trim — only obvious background, keep full page content."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    paper = ((gray > 135) & (hsv[:, :, 1] < 85)) | (gray > 200)
    if not paper.any():
        return bgr
    ys, xs = np.where(paper)
    pad = max(4, int(min(bgr.shape[:2]) * 0.008))
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(bgr.shape[0], int(ys.max()) + pad + 1)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(bgr.shape[1], int(xs.max()) + pad + 1)
    return bgr[y0:y1, x0:x1]


def _enhance(bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    pil = ImageOps.autocontrast(pil, cutoff=1)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def process_image(path: Path) -> np.ndarray:
    raw = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if raw is None:
        raise RuntimeError(f"cannot read {path}")
    doc = extract_document(raw)
    doc = auto_orient(doc)
    doc = trim_paper(doc)
    return _enhance(doc)


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def save_jpeg(bgr: np.ndarray, dest: Path, quality: int = 92) -> None:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(dest, "JPEG", quality=quality, optimize=True)


def build_pdf(jpg_paths: list[Path], pdf_path: Path) -> None:
    if not jpg_paths:
        return
    pages = [Image.open(p).convert("RGB") for p in jpg_paths]
    first, rest = pages[0], pages[1:]
    first.save(pdf_path, "PDF", save_all=True, append_images=rest, resolution=150.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", type=Path, default=ROOT / "data/scans/incoming")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data/scans/processed")
    ap.add_argument("--pdf-name", default="documents.pdf")
    args = ap.parse_args()

    in_dir = args.in_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(in_dir.glob("*.jpg")) + sorted(in_dir.glob("*.jpeg"))
    sources += sorted(in_dir.glob("*.JPG")) + sorted(in_dir.glob("*.JPEG"))
    if not sources:
        print("No JPEG files in", in_dir, file=sys.stderr)
        sys.exit(1)

    seen_hashes: set[str] = set()
    saved: list[Path] = []
    page = 0
    for src in sources:
        digest = file_hash(src)
        if digest in seen_hashes:
            print(f"  skip duplicate: {src.name}")
            continue
        seen_hashes.add(digest)
        page += 1
        out = out_dir / f"{page:03d}.jpg"
        try:
            result = process_image(src)
            save_jpeg(result, out)
            saved.append(out)
            print(f"  {page:03d} <- {src.name} ({result.shape[1]}x{result.shape[0]})")
        except Exception as e:
            print(f"  FAIL {src.name}: {e}", file=sys.stderr)

    pdf_path = out_dir / args.pdf_name
    build_pdf(saved, pdf_path)
    print(f"Done: {len(saved)} pages -> {out_dir}")
    if saved:
        print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
