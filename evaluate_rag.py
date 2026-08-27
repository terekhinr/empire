#!/usr/bin/env python3
"""
LLM-as-a-Judge: автоматическая оценка качества RAG + генерации Empire.

Запуск из корня репозитория:
  ./venv/bin/python evaluate_rag.py
  ./venv/bin/python evaluate_rag.py --judge openai/gpt-4o
  ./venv/bin/python evaluate_rag.py --judge anthropic/claude-3.5-haiku --skip-gen

По умолчанию судья: GPT-4o с fallback на Claude 3.5 Haiku → DeepSeek (если premium недоступен на OpenRouter).

Требует: vector_db/{persona}/, OPENROUTER_API_KEY в .env
Первый запуск может скачать sentence-transformers (~500 MB).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import pickle
import re
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import faiss
import httpx
from dotenv import load_dotenv
from tabulate import tabulate

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["EMPIRE_SKIP_EMBEDDINGS"] = "0"
os.environ.setdefault("TELEGRAM_TOKEN", "0000000000:EVAL_RAG")
os.environ.setdefault("ADMIN_ID", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///empire.db")

load_dotenv(ROOT / ".env")

from tools.llm_client import (  # noqa: E402
    JUDGE_FALLBACK_CHAIN,
    chat,
    chat_with_fallback,
    openrouter_chat,
)

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GEN_MODEL_DEFAULT = "deepseek/deepseek-v3.2"
JUDGE_MODEL_DEFAULT = "openai/gpt-4o"

# ── 5 сложных тестовых вопросов ──

TEST_QUESTIONS: list[dict] = [
    {
        "persona": "gdepar",
        "question": (
            "[Инженерия] Парогенератор против электрокаменки: "
            "если в парилке стабильно 40–55% влажности и потолок «сухой» — "
            "как меняется стратегия вентиляции и долив без перегрева камней?"
        ),
    },
    {
        "persona": "stern",
        "question": (
            "[Биомеханика] Bird-dog (птица-собака) при дискогенной боли L4–L5 "
            "без обострения: что именно даёт McGill про anti-extension и "
            "как не превратить упражнение в гиперэкстензию поясницы?"
        ),
    },
    {
        "persona": "lenin",
        "question": (
            "[Анализ] Продразвёрстку 1921 и переход к нэп: "
            "как Ленин связывал продналог с крестьянским хозяйством — "
            "без сюжета про газеты, цензуру и «Сим победиши»."
        ),
    },
    {
        "persona": "garden",
        "question": (
            "[Почва] Кислый торфяник под клубнику: "
            "какие именно дозировки извести/доломита и сроки внесения "
            "до посадки, если pH 4.2–4.5 и высокий марганец в анализе?"
        ),
    },
    {
        "persona": "pension",
        "question": (
            "[Риск] Антихрупкость по Талебу vs «barbell strategy»: "
            "как распределить 30% «безопасных» активов при инфляции 8–10% "
            "и ограниченном доступе к USD — без общих советов «диверсифицируй»?"
        ),
    },
]

PERSONAS: dict[str, dict[str, str]] = {
    "garden": {
        "role": (
            "Агроном Степаныч. Природное земледелие. "
            "Пишешь сразу по делу, без воды и шаблонных вступлений."
        ),
    },
    "lenin": {
        "role": "В.И. Ленин. Исторический архив. Конкретные факты, даты, цитаты.",
    },
    "stern": {
        "role": (
            "Канал «Снегири · здоровый позвоночник» — методист по спине. "
            "Опираешься на МакГилла (Big-3, Back Mechanic). Коротко по форме, "
            "развёрнуто по сути, без шаблона «4 секции»."
        ),
    },
    "gdepar": {
        "role": (
            "Михалыч — банщик с 30-летним стажем. Простой разговорный русский. "
            "Говорит про температуру, влажность, вентиляцию, долив, типичные ошибки."
        ),
    },
    "pension": {
        "role": (
            "Аналитик финансов: тезис → факты из источников (Талеб, Хулиномика) → вывод. "
            "Без общих фраз «диверсифицируйте портфель»."
        ),
    },
}

_EMBEDDER = None
_INDEX_CACHE: dict[str, tuple] = {}


@dataclass
class RagContext:
    persona: str
    query: str
    kb_content: str
    kb_limit: int
    k_docs: int
    chunk_count: int = 0
    error: str | None = None


@dataclass
class JudgeScores:
    faithfulness: int
    answer_relevance: int
    information_density: int
    reasoning: str = ""
    raw_response: str = ""


@dataclass
class EvalResult:
    persona: str
    question: str
    answer: str
    rag: RagContext
    scores: JudgeScores | None = None
    gen_error: str | None = None
    judge_error: str | None = None
    judge_model_used: str | None = None


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        from sentence_transformers import SentenceTransformer

        _EMBEDDER = SentenceTransformer(EMBED_MODEL)
    return _EMBEDDER


def _load_faiss_index(persona: str):
    if persona in _INDEX_CACHE:
        return _INDEX_CACHE[persona]

    db_path = ROOT / "vector_db" / persona
    if not db_path.is_dir():
        raise FileNotFoundError(f"нет индекса {db_path}")

    index = faiss.read_index(str(db_path / "index.faiss"))
    with open(db_path / "index.pkl", "rb") as f:
        docstore, index_to_docstore_id = pickle.load(f)

    _INDEX_CACHE[persona] = (index, docstore, index_to_docstore_id)
    return _INDEX_CACHE[persona]


def _extract_query(question: str) -> str:
    m = re.match(r"\[(.*?)\]\s*(.*)", question, re.S)
    return m.group(2).strip() if m else question.strip()


def retrieve_context(persona: str, question: str) -> RagContext:
    """RAG retrieval без LangChain: FAISS + sentence-transformers."""
    query = _extract_query(question)

    if persona == "lenin":
        k_docs = 8
    elif persona == "pension":
        k_docs = 10
    else:
        k_docs = 5

    kb_limit = 8000 if persona in ("lenin", "pension") else 4000

    try:
        index, docstore, index_to_docstore_id = _load_faiss_index(persona)
    except FileNotFoundError as e:
        return RagContext(persona, query, "", kb_limit, k_docs, error=str(e))
    except Exception as e:
        return RagContext(persona, query, "", kb_limit, k_docs, error=str(e))

    embedder = _get_embedder()
    vec = embedder.encode([query], normalize_embeddings=True).astype("float32")
    _, indices = index.search(vec, k_docs * 2)

    docs = []
    for idx in indices[0]:
        if idx < 0:
            continue
        doc_id = index_to_docstore_id[int(idx)]
        docs.append(docstore._dict[doc_id])

    if persona == "lenin":
        try:
            import lenin_content

            docs = lenin_content.filter_lenin_kb_docs(docs, [])
        except Exception:
            pass

    if persona == "pension":
        docs = [d for d in docs if d.metadata.get("kind") != "txt"]
        docs = [
            d
            for d in docs
            if "scripts/" not in str(d.metadata.get("source", ""))
            and "reference/" not in str(d.metadata.get("source", ""))
        ]

    docs = docs[:k_docs]
    kb_lines: list[str] = []
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

    kb_content = "\n\n".join(kb_lines)[:kb_limit]
    return RagContext(persona, query, kb_content, kb_limit, k_docs, chunk_count=len(docs))


def _format_api_error(data: dict | str | None) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or err)
        if err:
            return str(err)
        return str(data)
    return str(data or "unknown error")


def _build_generation_prompt(persona: str, question: str, rag: RagContext) -> str:
    role = PERSONAS[persona]["role"]
    topic = _extract_query(question)

    topic_rules = (
        "СТИЛЬ: связный текст короткими абзацами, без канцелярита и воды.\n"
        "Опирайся ТОЛЬКО на БАЗУ ЗНАНИЙ ниже. Если факта нет в базе — не выдумывай.\n"
        f"Пиши на тему: {topic}.\n"
    )

    kb_block = rag.kb_content.strip() or "(база знаний пуста — явно скажи, что данных недостаточно)"

    return (
        f"ИНСТРУКЦИЯ: {role}\n"
        f"ПРАВИЛА: {topic_rules}\n"
        f"БАЗА ЗНАНИЙ (цитируй по номеру источника [n], не выдумывай страницы):\n{kb_block}\n\n"
        "ЗАДАНИЕ: напиши готовый ответ для пользователя (700–1200 знаков). "
        "Только текст ответа, без секции ПРОМПТ и без мета-комментариев."
    )


async def generate_answer(persona: str, question: str, rag: RagContext, model: str) -> tuple[str, str | None]:
    prompt = _build_generation_prompt(persona, question, rag)
    temp = 0.55 if persona == "gdepar" else 0.2
    status, content, data = await chat(model, prompt, temperature=temp)

    if status != 200 or not content.strip():
        err = data.get("error") if isinstance(data, dict) else f"HTTP {status}"
        return "", str(err)

    # Убрать возможный блок ПРОМПТ: как в production
    parts = re.split(r"(?im)^\s*ПРОМПТ:\s*\*?\s*$", content, maxsplit=1)
    answer = parts[0].strip()
    return answer, None


JUDGE_SYSTEM = """Ты — строгий эксперт-оценщик RAG-систем. Оцени ОТВЕТ модели по извлечённому КОНТЕКСТУ и ВОПРОСУ пользователя.

Шкала 1–5 для каждой метрики:
- faithfulness: насколько ответ базируется ИСКЛЮЧИТЕЛЬНО на контексте (5 = всё из контекста, 1 = много галлюцинаций).
- answer_relevance: насколько ответ решает проблему пользователя без общих фраз и воды (5 = прямой точный ответ, 1 = оффтоп/вода).
- information_density: плотность полезных фактов — сколько конкретных утверждений на 100 слов (5 = много цифр/фактов/шагов, 1 = пустые обобщения).

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{
  "faithfulness": <int 1-5>,
  "answer_relevance": <int 1-5>,
  "information_density": <int 1-5>,
  "reasoning": "<2-4 предложения на русском: что хорошо, что плохо>"
}"""


def _parse_judge_json(text: str) -> JudgeScores:
    raw = text.strip()
    # Снять ```json ... ``` если модель обернула
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fence:
        raw = fence.group(1)

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"JSON не найден в ответе судьи: {text[:300]}")

    obj = json.loads(raw[start : end + 1])

    def _clamp_score(key: str) -> int:
        val = int(obj[key])
        return max(1, min(5, val))

    return JudgeScores(
        faithfulness=_clamp_score("faithfulness"),
        answer_relevance=_clamp_score("answer_relevance"),
        information_density=_clamp_score("information_density"),
        reasoning=str(obj.get("reasoning", "")).strip(),
        raw_response=text,
    )


def _judge_model_chain(preferred: str) -> list[str]:
    chain: list[str] = []
    for m in (preferred, *JUDGE_FALLBACK_CHAIN):
        if m and m not in chain:
            chain.append(m)
    return chain


async def judge_answer(
    question: str,
    context: str,
    answer: str,
    model: str,
    *,
    allow_fallback: bool = True,
) -> tuple[JudgeScores | None, str | None, str | None]:
    user_block = (
        f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{question}\n\n"
        f"ИЗВЛЕЧЁННЫЙ КОНТЕКСТ (единственный допустимый источник фактов):\n"
        f"{context or '(пусто)'}\n\n"
        f"ОТВЕТ RAG-СИСТЕМЫ:\n{answer}\n"
    )
    prompt = f"{JUDGE_SYSTEM}\n\n---\n\n{user_block}"

    models = _judge_model_chain(model) if allow_fallback else [model]
    last_err = ""

    for judge_model in models:
        status, content, data = await chat(
            judge_model, prompt, temperature=0.0, max_tokens=1024
        )
        if status != 200 or not content.strip():
            last_err = _format_api_error(data if isinstance(data, dict) else f"HTTP {status}")
            if status in (403, 404) and allow_fallback and judge_model != models[-1]:
                print(f"    ↳ {judge_model} недоступен, fallback…")
                continue
            return None, last_err, judge_model

        try:
            scores = _parse_judge_json(content)
            return scores, None, judge_model
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_err = f"не удалось разобрать JSON судьи ({judge_model}): {e}"
            if allow_fallback and judge_model != models[-1]:
                print(f"    ↳ {last_err}, fallback…")
                continue
            return None, f"{last_err}; raw={content[:400]}", judge_model

    return None, last_err or "судья недоступен", models[-1] if models else model


async def evaluate_case(
    case: dict,
    *,
    gen_model: str,
    judge_model: str,
    skip_gen: bool,
    no_judge_fallback: bool = False,
) -> EvalResult:
    persona = case["persona"]
    question = case["question"]

    print(f"\n▶ [{persona}] RAG retrieval…")
    rag = retrieve_context(persona, question)
    if rag.error:
        print(f"  ⚠ RAG: {rag.error}")
    else:
        print(f"  ✓ {rag.chunk_count} чанков, {len(rag.kb_content)} симв. контекста")

    answer = ""
    gen_error = None
    if skip_gen:
        answer = "(генерация пропущена — --skip-gen)"
        gen_error = "skip-gen"
    else:
        print(f"  → генерация ({gen_model})…")
        answer, gen_error = await generate_answer(persona, question, rag, gen_model)
        if gen_error:
            print(f"  ⚠ генерация: {gen_error}")
        else:
            print(f"  ✓ ответ: {len(answer)} симв.")

    scores = None
    judge_error = None
    judge_model_used = None
    if not skip_gen and answer and not gen_error:
        print(f"  → судья ({judge_model})…")
        scores, judge_error, judge_model_used = await judge_answer(
            question,
            rag.kb_content,
            answer,
            judge_model,
            allow_fallback=not no_judge_fallback,
        )
        if judge_error:
            print(f"  ⚠ судья: {judge_error}")
        elif scores:
            used = judge_model_used or judge_model
            if used != judge_model:
                print(f"  ℹ использован fallback-модель: {used}")
            print(
                f"  ✓ F={scores.faithfulness} R={scores.answer_relevance} "
                f"D={scores.information_density}"
            )

    return EvalResult(
        persona=persona,
        question=question,
        answer=answer,
        rag=rag,
        scores=scores,
        gen_error=gen_error,
        judge_error=judge_error,
        judge_model_used=judge_model_used,
    )


def _avg_score(scores: JudgeScores | None) -> float | None:
    if not scores:
        return None
    return round(
        (scores.faithfulness + scores.answer_relevance + scores.information_density) / 3,
        2,
    )


def print_summary_table(results: list[EvalResult], judge_model: str) -> None:
    rows = []
    for i, r in enumerate(results, 1):
        s = r.scores
        q_short = textwrap.shorten(_extract_query(r.question), width=42, placeholder="…")
        if s:
            rows.append(
                [
                    i,
                    r.persona,
                    q_short,
                    s.faithfulness,
                    s.answer_relevance,
                    s.information_density,
                    _avg_score(s),
                ]
            )
        else:
            err = r.judge_error or r.gen_error or r.rag.error or "—"
            rows.append([i, r.persona, q_short, "—", "—", "—", textwrap.shorten(str(err), width=30, placeholder="…")])

    headers = ["#", "Persona", "Вопрос", "Faith.", "Relev.", "Density", "Avg"]
    print("\n" + "═" * 96)
    print(f"  RAG Evaluation — LLM-as-Judge ({judge_model})")
    print("═" * 96)
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline", floatfmt=".2f"))
    print()

    scored = [r for r in results if r.scores]
    if scored:
        avg_f = sum(r.scores.faithfulness for r in scored) / len(scored)
        avg_r = sum(r.scores.answer_relevance for r in scored) / len(scored)
        avg_d = sum(r.scores.information_density for r in scored) / len(scored)
        print(
            f"  Среднее по {len(scored)} кейсам: "
            f"Faithfulness={avg_f:.2f}  Relevance={avg_r:.2f}  "
            f"Density={avg_d:.2f}  Overall={(avg_f + avg_r + avg_d) / 3:.2f}"
        )
        print()


def save_csv(results: list[EvalResult], path: Path, *, gen_model: str, judge_model: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    fieldnames = [
        "timestamp_utc",
        "persona",
        "question",
        "faithfulness",
        "answer_relevance",
        "information_density",
        "average",
        "gen_model",
        "judge_model",
        "judge_model_used",
        "rag_chunks",
        "rag_chars",
        "answer_chars",
        "judge_reasoning",
        "gen_error",
        "judge_error",
        "rag_error",
        "answer_preview",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            s = r.scores
            w.writerow(
                {
                    "timestamp_utc": ts,
                    "persona": r.persona,
                    "question": r.question,
                    "faithfulness": s.faithfulness if s else "",
                    "answer_relevance": s.answer_relevance if s else "",
                    "information_density": s.information_density if s else "",
                    "average": _avg_score(s) if s else "",
                    "gen_model": gen_model,
                    "judge_model": judge_model,
                    "judge_model_used": r.judge_model_used or "",
                    "rag_chunks": r.rag.chunk_count,
                    "rag_chars": len(r.rag.kb_content),
                    "answer_chars": len(r.answer),
                    "judge_reasoning": s.reasoning if s else "",
                    "gen_error": r.gen_error or "",
                    "judge_error": r.judge_error or "",
                    "rag_error": r.rag.error or "",
                    "answer_preview": textwrap.shorten(r.answer.replace("\n", " "), width=500, placeholder="…"),
                }
            )

    print(f"  CSV сохранён: {path}")


def print_detailed_reasoning(results: list[EvalResult]) -> None:
    for r in results:
        if not r.scores or not r.scores.reasoning:
            continue
        print(f"── {r.persona} ──")
        print(textwrap.fill(r.scores.reasoning, width=92))
        print()


async def main_async(args: argparse.Namespace) -> int:
    if not args.skip_gen and not os.getenv("OPENROUTER_API_KEY", "").strip():
        print("⚠ OPENROUTER_API_KEY не задан в .env — задайте ключ или используйте --skip-gen")
        return 1

    print("Empire RAG Evaluator (LLM-as-Judge)")
    print(f"  Генератор: {args.gen_model}")
    print(f"  Судья:     {args.judge_model}")
    print(f"  Кейсов:    {len(TEST_QUESTIONS)}")

    results: list[EvalResult] = []
    for case in TEST_QUESTIONS:
        res = await evaluate_case(
            case,
            gen_model=args.gen_model,
            judge_model=args.judge_model,
            skip_gen=args.skip_gen,
            no_judge_fallback=args.no_judge_fallback,
        )
        results.append(res)

    print_summary_table(results, args.judge_model)
    if args.verbose:
        print_detailed_reasoning(results)

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    save_csv(results, out_path, gen_model=args.gen_model, judge_model=args.judge_model)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM-as-Judge оценка RAG Empire")
    p.add_argument(
        "--judge",
        dest="judge_model",
        default=os.getenv("RAG_JUDGE_MODEL", JUDGE_MODEL_DEFAULT),
        help=f"Модель-судья OpenRouter (default: {JUDGE_MODEL_DEFAULT})",
    )
    p.add_argument(
        "--gen-model",
        default=os.getenv("RAG_GEN_MODEL", GEN_MODEL_DEFAULT),
        help=f"Модель генерации (default: {GEN_MODEL_DEFAULT})",
    )
    p.add_argument(
        "--output",
        default=f"logs/rag_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        help="Путь к CSV-логу",
    )
    p.add_argument("--skip-gen", action="store_true", help="Только RAG retrieval, без LLM")
    p.add_argument(
        "--no-judge-fallback",
        action="store_true",
        help="Не переключаться на fallback-модель судьи при 403/404",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Показать reasoning судьи")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
