#!/usr/bin/env python3
"""Извлечь дневные строки Кизимы → data/garden_kizima_calendar.json.

Источники:
1. Regex «N месяца …» по текстовому слою всех PDF.
2. PDF «лунный календарь … 2025г.»: OCR таблиц фаз + «Работы в <месяце>» → все дни года.
"""

from __future__ import annotations

import calendar
import io
import json
import re
from pathlib import Path

import fitz
import PyPDF2
import pytesseract
from io import BytesIO
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "garden_kizima_calendar.json"
LUNAR_2025_PDF = (
    REPO
    / "data"
    / "garden"
    / "Кизима Г. - Лунный посевной календарь садовода и огородника на 2025г. - 2024.pdf"
)
LUNAR_FULL_PDF = (
    REPO
    / "data"
    / "garden"
    / "Кизима Г.А. - Самый полный лунный посевной календарь сад. и огор. на 2020-2029 гг. (Календарь СиО) - 2019.pdf"
)
MONTH_FROM_DNI = {
    "январ": 1,
    "феврал": 2,
    "марта": 3,
    "апрел": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS)}
MONTH_WORKS_TITLE = {
    "январе": 1,
    "феврале": 2,
    "марте": 3,
    "апреле": 4,
    "мае": 5,
    "июне": 6,
    "июле": 7,
    "августе": 8,
    "сентябре": 9,
    "октябре": 10,
    "ноябре": 11,
    "декабре": 12,
}
PHASE_REC = {
    1: "Фаза I: посев, прополка, опрыскивание (по лунному календарю).",
    2: "Фаза II: посадка, полив, подкормка.",
    3: "Фаза III: посадка, полив, подкормка.",
    4: "Фаза IV: посев, прополка, опрыскивание.",
}


def extract_from_pdf(path: Path, year: int) -> list[dict]:
    text = re.sub(
        r"\s+",
        " ",
        "\n".join((p.extract_text() or "") for p in PyPDF2.PdfReader(BytesIO(path.read_bytes())).pages),
    )
    entries: list[dict] = []
    for mon in MONTHS:
        pat = rf"(\d{{1,2}})\s+{mon}\s+([^\.]{{12,320}}(?:\.[^\.]{{0,80}})?)"
        for m in re.finditer(pat, text, re.I):
            day = int(m.group(1))
            body = m.group(2).strip()
            if len(body) < 12:
                continue
            entries.append(_entry(day, MONTH_NUM[mon], year, body, path))
    return entries


def _entry(day: int, month: int, year: int, text: str, path: Path) -> dict:
    return {
        "day": day,
        "month": month,
        "year": year,
        "text": text,
        "source": f"Г. Кизима, лунный посевной календарь ({path.stem[:40]}…)",
    }


def _ocr_page_image(doc: fitz.Document, page: fitz.Page, zoom: float = 3.0) -> str:
    imgs = page.get_images(full=True)
    if not imgs:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    else:
        base = doc.extract_image(imgs[0][0])
        img = Image.open(io.BytesIO(base["image"]))
        w, h = img.size
        img = img.resize((int(w * zoom), int(h * zoom)), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(ImageOps.grayscale(img))
    return pytesseract.image_to_string(gray, lang="rus+eng", config="--psm 6")


def parse_period_starts_from_text(text: str) -> list[int]:
    """Дни начала лунных периодов из блока «Дата и время … начала периода»."""
    m = re.search(
        r"Дата и время\s*(.+?)\s*начала периода",
        text,
        flags=re.S | re.I,
    )
    if not m:
        return []
    row = m.group(1)
    nums = [int(x) for x in re.findall(r"\b(\d{1,2})\b", row) if 1 <= int(x) <= 31]
    tail = text[m.end() : m.end() + 160]
    times = re.findall(r"\(\s*\d{1,2}[.:]\d{2}\s*\)", tail)
    if nums and times:
        return nums[: len(times)]
    return nums


def parse_period_starts_ocr(ocr: str) -> list[int]:
    """Fallback: OCR нижней части картинки месяца."""
    flat = re.sub(r"\s+", " ", ocr)
    starts = parse_period_starts_from_text(flat)
    if starts:
        return starts
    times = re.findall(r"\(\s*\d{1,2}\s*:\s*\d{2}\s*\)", flat)
    if not times:
        return []
    if "Дата и время" in flat and "начала периода" in flat:
        mid = flat.split("Дата и время", 1)[1].split("начала периода", 1)[0]
        nums = [int(x) for x in re.findall(r"\d{1,2}", mid) if 1 <= int(x) <= 31]
        if len(nums) >= len(times) - 1:
            while len(nums) < len(times):
                nums.append(min(31, (nums[-1] if nums else 1) + 7))
            return nums[: len(times)]
    return []


def load_2025_period_starts(full_pdf: Path) -> dict[int, list[int]]:
    """{month: [4, 12, 20, 27]} из раздела «2025 ГОД» полного календаря."""
    if not full_pdf.is_file():
        return {}
    doc = fitz.open(full_pdf)
    by_month: dict[int, list[int]] = {}
    for i in range(doc.page_count):
        text = doc[i].get_text() or ""
        if "2025 ГОД" not in text or "Дата и время" not in text:
            continue
        mon_m = re.search(r"Дни (\w+)", text, re.I)
        if not mon_m:
            continue
        key = mon_m.group(1).lower()
        month = next((n for k, n in MONTH_FROM_DNI.items() if key.startswith(k)), None)
        if not month:
            continue
        starts = parse_period_starts_from_text(text)
        if starts:
            by_month[month] = starts
    doc.close()
    return by_month


def day_lunar_phase(day: int, period_starts: list[int]) -> int:
    if not period_starts:
        return ((day - 1) // 7) % 4 + 1
    starts = sorted(period_starts)
    start = starts[0]
    for s in starts:
        if day >= s:
            start = s
    offset = max(0, day - start)
    return min(offset // 2 + 1, 4)


def parse_numbered_works(section: str) -> list[str]:
    section = re.sub(r"\s+", " ", section)
    items: list[str] = []
    for m in re.finditer(
        r"(?:^|\s)(\d+)\.\s+(.+?)(?=(?:\s\d+\.\s)|(?:\sПервая половина)|(?:\sВторая половина)|$)",
        section,
        flags=re.S,
    ):
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        if len(body) > 25:
            items.append(body)
    return items


def extract_monthly_works(doc: fitz.Document) -> dict[int, list[str]]:
    """{month_num: [работа1, работа2, …]} из блоков «Работы в …»."""
    by_month: dict[int, list[str]] = {}
    best_len: dict[int, int] = {}
    for i in range(doc.page_count):
        text = doc[i].get_text() or ""
        m = re.search(r"Работы в (\w+)", text)
        if not m:
            continue
        mon_word = m.group(1).lower()
        month = MONTH_WORKS_TITLE.get(mon_word)
        if not month:
            continue
        if len(text) < best_len.get(month, 0):
            continue
        items = parse_numbered_works(text)
        if len(items) >= 3:
            by_month[month] = items
            best_len[month] = len(text)
    return by_month


def spread_items_to_days(items: list[str], month: int) -> dict[int, str]:
    ndays = calendar.monthrange(2026, month)[1]
    if not items:
        return {}
    out: dict[int, str] = {}
    for idx, item in enumerate(items):
        d0 = int(idx * ndays / len(items)) + 1
        d1 = int((idx + 1) * ndays / len(items)) if idx < len(items) - 1 else ndays
        for d in range(d0, d1 + 1):
            out[d] = item
    return out


def extract_lunar_2025_calendar(path: Path, year: int = 2026) -> list[dict]:
    if not path.is_file():
        return []
    doc = fitz.open(path)
    works = extract_monthly_works(doc)
    period_by_month = load_2025_period_starts(LUNAR_FULL_PDF)

    if len(period_by_month) < 10:
        month_cursor = 1
        for i in range(doc.page_count):
            page = doc[i]
            if len(page.get_images(full=True)) != 1:
                continue
            if len((page.get_text() or "").strip()) > 30:
                continue
            ocr = _ocr_page_image(doc, page)
            starts = parse_period_starts_ocr(ocr)
            if starts and month_cursor <= 12:
                period_by_month[month_cursor] = starts
                month_cursor += 1

    entries: list[dict] = []
    src = "Г. Кизима, лунный посевной календарь 2025 (фазы + работы месяца)"
    for month in range(1, 13):
        day_works = spread_items_to_days(works.get(month, []), month)
        starts = period_by_month.get(month, [])
        ndays = calendar.monthrange(year, month)[1]
        for day in range(1, ndays + 1):
            phase = day_lunar_phase(day, starts)
            parts = [PHASE_REC[phase]]
            if day in day_works:
                work = day_works[day]
                if len(work) > 220:
                    work = work[:217].rsplit(" ", 1)[0] + "…"
                parts.append(work)
            if starts and day in starts:
                parts.insert(
                    0,
                    f"{day} {_MONTHS_SHORT(month)} — начало нового лунного периода.",
                )
            text = " ".join(parts)
            entries.append(
                {
                    "day": day,
                    "month": month,
                    "year": year,
                    "text": text,
                    "source": src,
                }
            )
    doc.close()
    return entries


def _MONTHS_SHORT(month: int) -> str:
    return MONTHS[month - 1]


def merge_entries(existing: list[dict], new: list[dict]) -> list[dict]:
    by_key: dict[tuple[int, int, int], dict] = {}
    for e in existing + new:
        k = (int(e["year"]), int(e["month"]), int(e["day"]))
        if k not in by_key:
            by_key[k] = e
            continue
        old = by_key[k]
        # Явная дата из regex важнее синтетики; длиннее — лучше
        old_syn = "фазы + работы" in (old.get("source") or "")
        new_syn = "фазы + работы" in (e.get("source") or "")
        if old_syn and not new_syn:
            by_key[k] = e
        elif not old_syn and new_syn:
            pass
        elif len(e.get("text", "")) > len(old.get("text", "")):
            by_key[k] = e
    return sorted(by_key.values(), key=lambda x: (x["month"], x["day"], x.get("year", 0)))


def main() -> None:
    garden = REPO / "data" / "garden"
    pdfs: list[Path] = []
    for pat in ("*календар*.pdf", "*Календар*.pdf", "*2025*.pdf", "*Кизима*.pdf"):
        pdfs.extend(garden.glob(pat))

    all_entries: list[dict] = []
    for path in sorted(set(pdfs)):
        if "вредител" in path.name.lower() or "болезн" in path.name.lower():
            continue
        year = 2026 if "2025г" in path.name or "2025г." in path.name else 2025
        if "2020-2029" in path.name or "2022" in path.name or "2031" in path.name:
            year = 2025
        all_entries.extend(extract_from_pdf(path, year))

    if LUNAR_2025_PDF.is_file():
        all_entries = merge_entries(all_entries, extract_lunar_2025_calendar(LUNAR_2025_PDF))

    by_key: dict[tuple[int, int, int], dict] = {}
    for e in merge_entries([], all_entries):
        k = (e["year"], e["month"], e["day"])
        by_key[k] = e
    out = sorted(by_key.values(), key=lambda x: (x["month"], x["day"]))
    OUT.write_text(json.dumps({"entries": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    may = [e for e in out if e["month"] == 5 and e.get("year") == 2026]
    print(f"OK {OUT} — {len(out)} записей (май 2026: {len(may)} дней)")
    e27 = next((e for e in out if e["month"] == 5 and e["day"] == 27 and e.get("year") == 2026), None)
    if e27:
        print(f"  27 мая: {e27['text'][:140]}…")


if __name__ == "__main__":
    main()
