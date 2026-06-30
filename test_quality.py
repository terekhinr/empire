#!/usr/bin/env python3
"""
Проба качества RAG + LLM (production-путь main.generate_draft_content).

Запуск из корня репозитория:
  ./venv/bin/python test_quality.py
  ./venv/bin/python test_quality.py --skip-llm          # только RAG, без OpenRouter
  ./venv/bin/python test_quality.py --no-selfcritique   # без 2-го прохода gdepar/проч.

Требует: vector_db/{persona}/, OPENROUTER_API_KEY (если не --skip-llm).
Первый запуск может скачать sentence-transformers (~500 MB).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# RAG нужен — не пропускать embeddings
os.environ["EMPIRE_SKIP_EMBEDDINGS"] = "0"
os.environ.setdefault("TELEGRAM_TOKEN", "0000000000:TEST_QUALITY_PROBE")
os.environ.setdefault("ADMIN_ID", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///empire.db")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

_EMBEDDINGS = None
_FAISS_CACHE: dict[str, object] = {}


def _get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _EMBEDDINGS

# ── 3 неочевидные темы (узкий угол, легко «сорваться» в воду / шаблон) ──

TEST_CASES: list[dict] = [
    {
        "persona": "gdepar",
        "topic_raw": (
            "[Инженерия] Парогенератор против электрокаменки: "
            "если в парилке стабильно 40–55% влажности и потолок «сухой» — "
            "как меняется стратегия вентиляции и долив без перегрева камней?"
        ),
        "why_hard": "Нужна инженерия, не чек-лист «2–3 захода + веник».",
    },
    {
        "persona": "stern",
        "topic_raw": (
            "[Биомеханика] Bird-dog (птица-собака) при дискогенной боли L4–L5 "
            "без обострения: что именно даёт McGill про anti-extension и "
            "как не превратить упражнение в гиперэкстензию поясницы?"
        ),
        "why_hard": "Должны быть цифры/формулировки из базы (McGill), не шаблон «4 секции».",
    },
    {
        "persona": "lenin",
        "topic_raw": (
            "[Анализ] Продразвёрстку 1921 и переход к нэп: "
            "как Ленин связывал продналог с крестьянским хозяйством — "
            "без сюжета про газеты, цenzуру и «Сим победиши»."
        ),
        "why_hard": "Узкая экономическая тема; модель любит прессу/канцелярию.",
    },
]

# Маркеры «ИИ-копипасты» (из main + типичные LLM-штампы)
AI_TEMPLATE_MARKERS = (
    "**анатомия движения**",
    "**техника шаг за шагом**",
    "**3 ошибки новичков**",
    "**прогрессия и безопасность**",
    "анатомия движения",
    "техника шаг за шагом",
    "3 ошибки новичков",
    "прогрессия и безопасность",
    "важно отметить",
    "важно понимать",
    "в заключение",
    "давайте разбер",
    "подведём итог",
    "в данной статье",
    "в этом посте",
    "дорогие друзья",
    "уважаемые читатели",
    "универсальный чек-лист",
    "не секрет, что",
    "актуально сегодня",
    "звучит особенно актуально",
    "парадокс? нет",
    "выходишь обновлённым",
    "священнодейств",
    "тишина в парилке",
    "верхняя полка",
    "замочи веник",
)

META_AI_RE = re.compile(
    r"(?i)(важно отметить|важно понимать|в заключение|подведём итог|"
    r"давайте разбер|не секрет, что|универсальн\w+ чек|актуально сегодня)"
)
NUM_RE = re.compile(
    r"\d+(?:[.,]\d+)?(?:\s*(?:%|°|°c|кг|г|мм|см|м|мин|сек|ч|лет|г\.|т\.|стр\.|квт))?",
    re.I,
)


def _normalize_nums(text: str) -> set[str]:
    """Сравнение цифр без OCR-дефисов и en-dash."""
    raw = NUM_RE.findall(text.replace("–", "-").replace("--", "-"))
    out: set[str] = set()
    for x in raw:
        core = re.sub(r"[^\d.,]", "", x.split()[0] if " " in x else x)
        if core:
            out.add(core.replace(",", "."))
    return out
WORD_RE = re.compile(r"[a-zа-яё]{5,}", re.I)


@dataclass
class RagResult:
    kb_content: str
    kb_limit: int
    k_docs: int
    query: str
    chunk_previews: list[str] = field(default_factory=list)
    error: str | None = None


def retrieve_rag_context(p_key: str, topic_raw: str) -> RagResult:
    """Зеркало логики main.generate_draft_content (load_kb блок)."""
    topic = topic_raw
    m = re.match(r"\[(.*?)\]\s*(.*)", topic_raw)
    if m:
        topic = m.group(2).strip()

    if p_key == "lenin":
        k_docs = 8
    elif p_key == "pension":
        k_docs = 10
    else:
        k_docs = 5

    kb_limit = 8000 if p_key in ("lenin", "pension") else 4000
    db_path = ROOT / "vector_db" / p_key

    if not db_path.is_dir():
        return RagResult("", kb_limit, k_docs, topic, error=f"нет индекса {db_path}")

    try:
        from langchain_community.vectorstores import FAISS

        emb = _get_embeddings()
        cache_key = str(db_path)
        if cache_key not in _FAISS_CACHE:
            _FAISS_CACHE[cache_key] = FAISS.load_local(
                str(db_path), emb, allow_dangerous_deserialization=True
            )
        db = _FAISS_CACHE[cache_key]
    except Exception as e:
        return RagResult("", kb_limit, k_docs, topic, error=str(e))

    raw_docs = db.similarity_search(topic, k=k_docs * 2)

    if p_key == "lenin":
        try:
            import lenin_content

            raw_docs = lenin_content.filter_lenin_kb_docs(raw_docs, [])
        except Exception:
            pass
    if p_key == "pension":
        raw_docs = [d for d in raw_docs if d.metadata.get("kind") != "txt"]
        raw_docs = [
            d
            for d in raw_docs
            if "scripts/" not in str(d.metadata.get("source", ""))
            and "reference/" not in str(d.metadata.get("source", ""))
        ]

    docs = raw_docs[:k_docs]
    kb_lines: list[str] = []
    previews: list[str] = []
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source", "?")
        pages = d.metadata.get("pages")
        line_no = d.metadata.get("line")
        head = f"[{i}] Источник: {src}"
        if pages:
            head += f", стр. {pages}"
        elif line_no is not None:
            head += f", календарь строка {line_no}"
        body = (d.page_content or "").strip()
        kb_lines.append(f"{head}\n{body}")
        previews.append(f"{head}\n{textwrap.shorten(body, width=280, placeholder='…')}")

    kb_content = "\n\n".join(kb_lines)
    return RagResult(kb_content[:kb_limit], kb_limit, k_docs, topic, previews)


def _body_without_hashtags(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    body = [ln for ln in lines if not ln.lstrip().startswith("#")]
    return "\n".join(body)


def _significant_tokens(text: str) -> set[str]:
    stop = {
        "который", "которая", "которые", "этого", "этому", "можно", "нужно",
        "очень", "просто", "только", "чтобы", "потому", "также", "будет",
        "если", "когда", "после", "перед", "через", "между", "внутри",
    }
    return {w.lower() for w in WORD_RE.findall(text) if w.lower() not in stop and len(w) > 5}


def score_ai_slop(post: str, p_key: str) -> tuple[int, list[str]]:
    """10 = максимально «ИИ-копипаста», 1 = живой текст."""
    body = _body_without_hashtags(post).lower()
    notes: list[str] = []
    penalty = 0

    for ph in AI_TEMPLATE_MARKERS:
        if ph.lower() in body:
            penalty += 2 if "анатомия" in ph or "техника шаг" in ph else 1
            notes.append(f"штамп/шаблон: «{ph}»")

    try:
        import main as m

        banned = m._SELFCRITIC_BANNED_PHRASES.get(p_key, ())
        for ph in banned:
            if ph in body:
                penalty += 1
                notes.append(f"ban-list ({p_key}): «{ph}»")
    except Exception:
        pass

    meta_hits = META_AI_RE.findall(body)
    if meta_hits:
        penalty += len(meta_hits)
        notes.append(f"мета-обращения: {meta_hits[:3]}")

    # Жирные подзаголовки markdown → типичный Stern-шаблон
    if re.search(r"\*\*[^*]{4,40}\*\*", post):
        penalty += 1
        notes.append("жирные подзаголовки **…** (часто LLM-структура)")

    bullets = len(re.findall(r"(?m)^\s*[•\-]\s+", post))
    numbered = len(re.findall(r"(?m)^\s*\d+[\).]\s+", post))
    if bullets + numbered >= 6:
        penalty += 1
        notes.append(f"много списков ({bullets} буллетов, {numbered} нумераций)")

    if len(body) < 400:
        penalty += 1
        notes.append("короткий пост (<400 знаков тела) — часто «вода»")

    score = max(1, min(10, 3 + penalty))
    if not notes:
        notes.append("явных ИИ-маркеров мало")
    return score, notes


def score_factual_grounding(post: str, rag: RagResult) -> tuple[int, list[str]]:
    """10 = много конкретики, согласованной с RAG; 1 = пустота / отрыв от базы."""
    body = _body_without_hashtags(post)
    notes: list[str] = []
    points = 0

    if rag.error:
        notes.append(f"RAG error: {rag.error}")
        return 1, notes
    if not rag.kb_content.strip():
        notes.append("RAG вернул пустой контекст — LLM работала без базы")
        return 1, notes

    rag_nums = _normalize_nums(rag.kb_content)
    post_nums = _normalize_nums(body)
    overlap_nums = rag_nums & post_nums
    if post_nums:
        ratio = len(overlap_nums) / max(1, len(post_nums))
        if ratio >= 0.35:
            points += 3
            notes.append(f"цифры из RAG: {len(overlap_nums)}/{len(post_nums)} совпали")
        elif overlap_nums:
            points += 1
            notes.append(f"мало общих цифр с RAG: {list(overlap_nums)[:5]}")
        else:
            notes.append("цифры в посте не пересекаются с RAG — риск галлюцинаций")
    else:
        notes.append("в посте нет конкретных цифр/единиц")

    rag_tok = _significant_tokens(rag.kb_content)
    post_tok = _significant_tokens(body)
    if rag_tok and post_tok:
        j = len(rag_tok & post_tok) / len(post_tok)
        if j >= 0.12:
            points += 3
            notes.append(f"лексика RAG→пост: {j:.0%} значимых слов поста есть в KB")
        elif j >= 0.05:
            points += 1
            notes.append(f"слабая лексическая связь с KB: {j:.0%}")
        else:
            notes.append(f"пост почти не пересекается с KB лексически ({j:.0%})")

    # Имена/фамилии/аббревиатуры из RAG
    rag_caps = set(re.findall(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b", rag.kb_content))
    rag_caps |= set(re.findall(r"\b[A-Z]{2,5}\b", rag.kb_content))
    found_names = [n for n in rag_caps if n in body and len(n) > 3][:5]
    if found_names:
        points += 2
        notes.append(f"имена/термины из KB в посте: {found_names}")
    else:
        notes.append("нет явных имён/терминов из KB в тексте поста")

    if len(body) >= 900:
        points += 1
        notes.append("длина тела ≥900 — есть пространство для фактуры")
    elif len(body) < 500:
        notes.append("короткий пост — мало места для фактов")

    if re.search(r"\[[0-9]+\]", body):
        notes.append("в посте остались маркеры [n] — сломан finalize")

    score = max(1, min(10, points + 1))
    return score, notes


def _print_block(title: str, content: str, width: int = 88) -> None:
    bar = "═" * width
    print(f"\n{bar}\n{title}\n{bar}")
    if not content.strip():
        print("  (пусто)")
    else:
        for line in content.splitlines():
            print(textwrap.fill(line, width=width, subsequent_indent="  ") if len(line) > width else line)


async def run_case(case: dict, *, skip_llm: bool, no_selfcritique: bool) -> None:
    p_key = case["persona"]
    topic_raw = case["topic_raw"]

    print("\n" + "█" * 88)
    print(f"  КЕЙС: {p_key.upper()} — {case['why_hard']}")
    print(f"  ТЕМА: {topic_raw}")
    print("█" * 88)

    rag = retrieve_rag_context(p_key, topic_raw)
    _print_block(
        f"RAG — сырой контекст (top-{rag.k_docs}, limit {rag.kb_limit} симв., query={rag.query!r})",
        rag.kb_content if rag.kb_content else (rag.error or "(пусто)"),
    )
    if rag.chunk_previews:
        print("\n── Превью чанков ──")
        for p in rag.chunk_previews:
            print(textwrap.indent(p, "  "))
            print()

    if skip_llm:
        print("\n[--skip-llm] LLM не вызывалась.\n")
        return

    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        print("\n⚠ OPENROUTER_API_KEY не задан — пропуск LLM. Задайте ключ в .env\n")
        return

    import main

    async def _empty_hint(*_a, **_k):
        return ""

    async def _empty_bodies(*_a, **_k):
        return []

    main._topic_history_hint = _empty_hint
    main._recent_post_bodies = _empty_bodies

    orig_rewrite = main._selfcritique_rewrite
    orig_findings = main._selfcritique_findings

    async def _skip_rewrite(*_a, **_k):
        return None

    if no_selfcritique:
        main._selfcritique_rewrite = _skip_rewrite
        main._selfcritique_findings = lambda *_a, **_k: []

    try:
        post_text, img_prompt = await main.generate_draft_content(p_key, topic_raw)
    finally:
        if no_selfcritique:
            main._selfcritique_findings = orig_findings
            main._selfcritique_rewrite = orig_rewrite

    _print_block("LLM — финальный пост (после fix_html + finalize + self-critique)", post_text)
    if img_prompt and img_prompt != "Error":
        print(f"\n  (image prompt: {textwrap.shorten(str(img_prompt), 120)})")

    ai_score, ai_notes = score_ai_slop(post_text, p_key)
    fact_score, fact_notes = score_factual_grounding(post_text, rag)

    print("\n── ОЦЕНКА (эвристика по коду, не LLM-judge) ──")
    print(f"  ИИ-шность:     {ai_score}/10  (↑ хуже, похоже на копипасту)")
    for n in ai_notes:
        print(f"    • {n}")
    print(f"  Фактура/RAG:   {fact_score}/10  (↑ лучше, опора на базу)")
    for n in fact_notes:
        print(f"    • {n}")
    composite = max(1, min(10, round((11 - ai_score + fact_score) / 2)))
    print(f"  Сводный «продукт»: {composite}/10  (баланс живости и фактов)")


async def main_async(args: argparse.Namespace) -> None:
    cases = TEST_CASES
    if args.persona:
        cases = [c for c in cases if c["persona"] == args.persona]
        if not cases:
            print(f"Нет кейса для persona={args.persona!r}", file=sys.stderr)
            sys.exit(1)

    print("Empire RAG quality probe")
    print(f"  ROOT={ROOT}")
    print(f"  skip_llm={args.skip_llm}  no_selfcritique={args.no_selfcritique}")
    for case in cases:
        await run_case(case, skip_llm=args.skip_llm, no_selfcritique=args.no_selfcritique)
    print("\n" + "─" * 88)
    print("Готово. Интерпретация: ИИ-шность >7 или фактура <4 — сигнал пересмотра промптов/RAG.")


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG vs LLM quality side-by-side")
    ap.add_argument("--skip-llm", action="store_true", help="только retrieval, без OpenRouter")
    ap.add_argument(
        "--no-selfcritique",
        action="store_true",
        help="отключить 2-й проход self-critique (сырой 1-й ответ модели)",
    )
    ap.add_argument("--persona", choices=["gdepar", "stern", "lenin", "garden", "pension"])
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
