#!/usr/bin/env python3
"""
Сборка FAISS-индекса для RAG (тот же эмбеддинг, что в main.py).

Пример (Ленин, PDF из data/lenin):
  cd /root/projects/empire && ./venv/bin/python tools/build_rag.py --persona lenin

Перезапись vector_db/<persona>/ — с флагом --force.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from io import BytesIO
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

try:
    import docx as _python_docx  # python-docx
except Exception:
    _python_docx = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None  # type: ignore

# OCR — опционально. Если pytesseract/fitz/Pillow не установлены или
# системный tesseract отсутствует, OCR-фолбэк просто выключится.
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # type: ignore

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_CHARS = 1800
CHUNK_OVERLAP = 250
BATCH = 32
MIN_CHUNK = 120

# Сколько символов «настоящего» текста хотим увидеть на странице, чтобы НЕ
# считать PDF сканом. Меньше — почти наверняка картинка/нерасшифровываемый шрифт.
OCR_TRIGGER_AVG_CHARS_PER_PAGE = 40
OCR_TRIGGER_MIN_PAGES_CHECK = 3
OCR_DPI = 200
OCR_LANG = "rus+eng"
OCR_CACHE_DIR = Path("data") / "ocr_cache"


def _clean(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _split_oversized(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text] if text else []
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        if end < len(text):
            cut = text.rfind(". ", start + max_len // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + max_len // 2, end)
            if cut > start:
                end = cut + 1
        chunk = _clean(text[start:end])
        if len(chunk) >= MIN_CHUNK:
            parts.append(chunk)
        start = max(start + 1, end - CHUNK_OVERLAP)
    return parts


def _ocr_available() -> bool:
    if fitz is None or pytesseract is None or Image is None:
        return False
    # Проверяем, что бинарь tesseract реально доступен.
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_pdf_pages(pdf_bytes: bytes, pdf_name: str) -> list[tuple[int, str]]:
    """OCR PDF постранично. Кеш — в data/ocr_cache/<sha256>.json.
    Возвращает список (page_no, text). Если кеш есть — используется он."""
    if not _ocr_available():
        return []

    OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    cache_path = OCR_CACHE_DIR / f"{digest}.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return [(int(p), t) for p, t in cached.get("pages", [])]
        except Exception:
            pass

    pages: list[tuple[int, str]] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"  OCR open error {pdf_name}: {e}", file=sys.stderr)
        return []

    zoom = OCR_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    n = doc.page_count
    print(f"  OCR {pdf_name}: {n} стр., язык {OCR_LANG}, dpi {OCR_DPI}")
    for i in range(n):
        try:
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            mode = "RGB" if pix.n >= 3 else "L"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            text = pytesseract.image_to_string(img, lang=OCR_LANG)
        except Exception as e:
            print(f"    OCR page {i + 1} error: {e}", file=sys.stderr)
            text = ""
        text = (text or "").strip()
        if text:
            pages.append((i + 1, text))
        if (i + 1) % 25 == 0:
            print(f"    OCR прогресс: {i + 1}/{n}")
    doc.close()

    try:
        cache_path.write_text(
            json.dumps({"name": pdf_name, "pages": pages}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"  OCR cache write error: {e}", file=sys.stderr)
    return pages


def _docs_from_pages(name: str, pages: list[tuple[int, str]], max_chunks: int | None) -> list[Document]:
    """Собрать чанки из списка (page_no, text) — общий код для PyPDF2 и OCR."""
    docs: list[Document] = []
    buf = ""
    buf_start = pages[0][0] if pages else 1
    last_page = buf_start

    for pno, piece in pages:
        piece = _clean(piece)
        if not piece:
            continue
        if len(buf) + len(piece) + 2 < CHUNK_CHARS:
            buf = (buf + "\n\n" + piece).strip() if buf else piece
            last_page = pno
            continue
        if buf and len(buf) >= MIN_CHUNK:
            for part in _split_oversized(buf, CHUNK_CHARS):
                docs.append(
                    Document(
                        page_content=part,
                        metadata={"source": name, "pages": f"{buf_start}-{last_page}", "kind": "pdf"},
                    )
                )
        buf = piece
        buf_start = pno
        last_page = pno

    if buf and len(buf) >= MIN_CHUNK:
        for part in _split_oversized(buf, CHUNK_CHARS):
            docs.append(
                Document(
                    page_content=part,
                    metadata={"source": name, "pages": f"{buf_start}-{last_page}", "kind": "pdf"},
                )
            )

    if max_chunks is not None and len(docs) > max_chunks:
        docs = docs[:max_chunks]
    return docs


def pdf_to_documents(
    pdf_path: Path,
    skip_substrings: tuple[str, ...],
    max_chunks: int | None,
    ocr_mode: str = "auto",
) -> list[Document]:
    """ocr_mode: 'auto' | 'force' | 'off'.
    'auto' — пытаемся обычным экстрактором, при пустом результате идём в OCR."""
    name = pdf_path.name
    low = name.lower()
    for s in skip_substrings:
        if s.lower() in low:
            return []

    try:
        raw_bytes = pdf_path.read_bytes()
    except Exception as e:
        print(f"  SKIP PDF read error {name}: {e}", file=sys.stderr)
        return []

    pages: list[tuple[int, str]] = []
    needs_ocr = ocr_mode == "force"

    if ocr_mode != "force":
        try:
            reader = PyPDF2.PdfReader(BytesIO(raw_bytes))
        except Exception as e:
            print(f"  SKIP PDF read error {name}: {e}", file=sys.stderr)
            return []

        n_pages = len(reader.pages)
        sample_pages = min(n_pages, max(OCR_TRIGGER_MIN_PAGES_CHECK, 5))
        sample_chars = 0

        for i in range(n_pages):
            try:
                raw = reader.pages[i].extract_text() or ""
            except Exception:
                raw = ""
            piece = _clean(raw)
            if i < sample_pages:
                sample_chars += len(piece)
            if piece:
                pages.append((i + 1, piece))

        if ocr_mode == "auto":
            avg = sample_chars / max(1, sample_pages)
            # Считаем «скан», если первые страницы дают почти ноль текста.
            if avg < OCR_TRIGGER_AVG_CHARS_PER_PAGE:
                if _ocr_available():
                    needs_ocr = True
                    print(
                        f"  OCR-фолбэк {name}: avg={avg:.1f} симв/стр на первых {sample_pages} стр."
                    )
                else:
                    print(
                        f"  WARN PDF {name}: похоже на скан "
                        f"(avg={avg:.1f} симв/стр), но OCR недоступен — пропускаю как обычно."
                    )

    if needs_ocr:
        if not _ocr_available():
            print(f"  SKIP {name}: OCR запрошен, но недоступен", file=sys.stderr)
            return []
        ocr_pages = _ocr_pdf_pages(raw_bytes, name)
        if not ocr_pages:
            return []
        # OCR полностью заменяет (а не дополняет) текст: в скане PyPDF2 даёт мусор.
        pages = ocr_pages

    return _docs_from_pages(name, pages, max_chunks)


def _emit_long_text(name: str, kind: str, text: str) -> list[Document]:
    """Режет «обычный» длинный текст (txt/docx/html) на чанки."""
    docs: list[Document] = []
    text = _clean(text)
    if not text:
        return docs
    for part in _split_oversized(text, CHUNK_CHARS):
        if len(part) >= MIN_CHUNK:
            docs.append(Document(page_content=part, metadata={"source": name, "kind": kind}))
    return docs


def txt_to_documents(txt_path: Path) -> list[Document]:
    try:
        text = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return _emit_long_text(txt_path.name, "txt", text)


def docx_to_documents(docx_path: Path) -> list[Document]:
    if _python_docx is None:
        print(f"  SKIP DOCX (python-docx not installed): {docx_path.name}", file=sys.stderr)
        return []
    try:
        d = _python_docx.Document(str(docx_path))
        parts: list[str] = []
        for p in d.paragraphs:
            t = p.text.strip()
            if t:
                parts.append(t)
        text = "\n".join(parts)
    except Exception as e:
        print(f"  SKIP DOCX read error {docx_path.name}: {e}", file=sys.stderr)
        return []
    return _emit_long_text(docx_path.name, "docx", text)


def html_to_documents(html_path: Path) -> list[Document]:
    try:
        raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    if BeautifulSoup is None:
        # очень грубое удаление тегов, если bs4 не установлен
        text = re.sub(r"<[^>]+>", " ", raw)
    else:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(" ")
    return _emit_long_text(html_path.name, "html", text)


def calendar_txt_to_documents(txt_path: Path) -> list[Document]:
    docs: list[Document] = []
    try:
        text = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    for idx, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if len(line) < 10:
            continue
        docs.append(
            Document(
                page_content=line,
                metadata={"source": txt_path.name, "line": idx, "kind": "calendar"},
            )
        )
    return docs


def build(
    persona: str,
    input_dirs: list[Path],
    out_dir: Path,
    force: bool,
    skip_pdf: tuple[str, ...],
    max_chunks_per_pdf: int | None,
    max_pdf_bytes: int | None,
    ocr_mode: str,
) -> None:
    if out_dir.exists() and force:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Эмбеддинг {EMBED_MODEL} …")
    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    store: FAISS | None = None
    total_chunks = 0

    def ingest_batch(batch: list[Document]) -> None:
        nonlocal store, total_chunks
        if not batch:
            return
        for i in range(0, len(batch), BATCH):
            sub = batch[i : i + BATCH]
            if store is None:
                store = FAISS.from_documents(sub, emb)
            else:
                store.add_documents(sub)
        total_chunks += len(batch)

    for d in input_dirs:
        if not d.is_dir():
            print(f"  WARN: нет каталога {d}", file=sys.stderr)
            continue
        # Рекурсивный обход всех типов (включая статьи в подпапках, например crimson/).
        for pdf in sorted(d.rglob("*.pdf")):
            rel = pdf.relative_to(d).as_posix()
            # Сценарии/эталоны (Мячин) и справочные книги — не в фактологический RAG постов.
            if "/scripts/" in rel or rel.startswith("scripts/"):
                continue
            if "/reference/" in rel or rel.startswith("reference/"):
                continue
            if max_pdf_bytes and pdf.stat().st_size > max_pdf_bytes:
                print(
                    f"  SKIP huge PDF {pdf.name}: {pdf.stat().st_size//(1024*1024)} MiB > limit "
                    f"{max_pdf_bytes//(1024*1024)} MiB"
                )
                continue
            chunk_docs = pdf_to_documents(pdf, skip_pdf, max_chunks_per_pdf, ocr_mode)
            print(f"  PDF {pdf.relative_to(d)}: {len(chunk_docs)} чанков")
            ingest_batch(chunk_docs)
        for txt in sorted(d.rglob("*.txt")):
            low = txt.name.lower()
            if "calendar" in low:
                cdocs = calendar_txt_to_documents(txt)
                print(f"  TXT(calendar) {txt.relative_to(d)}: {len(cdocs)} строк")
            else:
                cdocs = txt_to_documents(txt)
                print(f"  TXT {txt.relative_to(d)}: {len(cdocs)} чанков")
            ingest_batch(cdocs)
        for dx in sorted(d.rglob("*.docx")):
            cdocs = docx_to_documents(dx)
            print(f"  DOCX {dx.relative_to(d)}: {len(cdocs)} чанков")
            ingest_batch(cdocs)
        for ext in ("*.html", "*.htm", "*.mhtml"):
            for hp in sorted(d.rglob(ext)):
                if "/scripts/" in hp.relative_to(d).as_posix() or hp.relative_to(d).as_posix().startswith("scripts/"):
                    continue
                if "/reference/" in hp.relative_to(d).as_posix() or hp.relative_to(d).as_posix().startswith("reference/"):
                    continue
                cdocs = html_to_documents(hp)
                print(f"  HTML {hp.relative_to(d)}: {len(cdocs)} чанков")
                ingest_batch(cdocs)

    if store is None or total_chunks == 0:
        print("Нет документов для индексации. Проверь пути.", file=sys.stderr)
        sys.exit(1)

    store.save_local(str(out_dir))
    repo = Path(__file__).resolve().parents[1]
    manifest_path = repo / "data" / f"rag_manifest_{persona}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "persona": persona,
        "chunks": total_chunks,
        "model": EMBED_MODEL,
        "chunk_chars": CHUNK_CHARS,
        "input_dirs": [str(p.resolve()) for p in input_dirs],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK → {out_dir}  (всего чанков: {total_chunks}, manifest: {manifest_path})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="lenin", help="ключ персоны (папка vector_db/<persona>)")
    ap.add_argument(
        "--input-dir",
        action="append",
        default=[],
        help="каталог с PDF/TXT (можно несколько раз)",
    )
    ap.add_argument("--output-dir", default="", help="по умолчанию vector_db/<persona>")
    ap.add_argument("--force", action="store_true", help="удалить старый индекс")
    ap.add_argument(
        "--skip-pdf-substring",
        action="append",
        default=["Алфавитный указатель"],
        help="не индексировать PDF, если имя содержит подстроку",
    )
    ap.add_argument(
        "--max-chunks-per-pdf",
        type=int,
        default=280,
        help="ограничение чанков на один PDF (защита от OOM на гигантских томах)",
    )
    ap.add_argument(
        "--max-pdf-mib",
        type=int,
        default=200,
        help="пропускать PDF тяжелее N МиБ (по умолчанию 200)",
    )
    ap.add_argument(
        "--ocr",
        choices=("auto", "force", "off"),
        default="auto",
        help="OCR-фолбэк для PDF-сканов: auto (по умолчанию), force, off",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    os.chdir(repo)

    default_dirs = [repo / "data" / args.persona, repo / "kb_sources" / args.persona]
    indirs = [Path(p) for p in args.input_dir] if args.input_dir else default_dirs
    out = Path(args.output_dir) if args.output_dir else repo / "vector_db" / args.persona

    skip_t = tuple(args.skip_pdf_substring)
    max_bytes = args.max_pdf_mib * 1024 * 1024 if args.max_pdf_mib > 0 else None
    build(
        args.persona, indirs, out, args.force, skip_t,
        args.max_chunks_per_pdf, max_bytes, args.ocr,
    )


if __name__ == "__main__":
    main()
