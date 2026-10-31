#!/usr/bin/env python3
"""Модерация отзывов pending → approve/hide через дешёвый LLM + локальный RAG (регламент).

  * RAG: data/review_moderation_rag.md режется по заголовкам ##, эмбеддинги
    sentence-transformers (локально, без оплаты), в промпт попадают top-K чанков
    по косинусной близости к объединённому тексту батча.
  * Батчинг: один запрос OpenRouter на N отзывов → JSON с решениями.
  * По умолчанию dry-run (только печать). --apply пишет в БД и обновляет reviews_total.
  * Ночной daily: по умолчанию после reviews вызывается этот скрипт с --apply, если задан
    OPENROUTER_API_KEY; выключить фазу: BANYA_DAILY_MODERATE_AI=0 (см. yandex_scrape.py).

Переменные окружения (.env):
  OPENROUTER_API_KEY — обязательно для не-dry вызова API
  BANYA_MODERATE_MODEL — по умолчанию deepseek/deepseek-chat
    (openai/* на аккаунте может отдавать 403 ToS)

Примеры:
  python3 tools/banya_review_moderate_ai.py                    # быстро: сколько pending, превью
  python3 tools/banya_review_moderate_ai.py --preview-api    # 1 батч: RAG+LLM, без записи в БД
  python3 tools/banya_review_moderate_ai.py --apply --batch-size 20 --max-batches 3
  python3 tools/banya_review_moderate_ai.py --apply --min-text 15 --source yandex --limit 50
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "empire.db"
RAG_PATH = ROOT / "data" / "review_moderation_rag.md"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = (
    os.getenv("BANYA_MODERATE_MODEL", "deepseek/deepseek-chat").strip()
    or "deepseek/deepseek-chat"
)
EMBED_MODEL = os.getenv(
    "BANYA_MODERATE_EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
).strip()


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def _split_rag_chunks(text: str) -> list[str]:
    parts = re.split(r"\n(?=## )", text.strip())
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        out.append(p[:3500])
    if not out:
        return [text.strip()[:8000]]
    return out


def _encode_st(model, texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    m: SentenceTransformer = model
    vecs = m.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [list(map(float, row)) for row in vecs]


def _top_chunks(
    query: str,
    chunk_embs: list[list[float]],
    chunks: list[str],
    k: int,
    model,
) -> str:
    qv = _encode_st(model, [query])[0]
    scored: list[tuple[float, int]] = []
    for i, cv in enumerate(chunk_embs):
        s = sum(a * b for a, b in zip(qv, cv))
        scored.append((s, i))
    scored.sort(reverse=True)
    pick = [chunks[i] for _, i in scored[:k]]
    return "\n\n---\n\n".join(pick)


def _refresh_counts(cur: sqlite3.Cursor, spot_ids: set[int], now: str) -> None:
    """Не трогаем reviews_total (счётчик Яндекса / посещаемость)."""
    for sid in spot_ids:
        cur.execute(
            "UPDATE banya_spots SET updated_at = ? WHERE id = ?",
            (now, sid),
        )


def _extract_json_object(raw: str) -> dict | None:
    raw = raw.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", raw)
    if m:
        raw = m.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> tuple[int, str, dict | None]:
    try:
        import httpx
    except ImportError:
        print("Нужен пакет httpx: pip install httpx", file=sys.stderr)
        return 0, "", None
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://gdepar.ru",
                "X-Title": "empire-banya-moderate",
            },
            json=payload,
        )
    try:
        data = r.json()
    except Exception:
        data = {}
    text = ""
    if r.status_code == 200 and isinstance(data, dict):
        ch = data.get("choices") or []
        if ch and isinstance(ch[0], dict):
            msg = ch[0].get("message") or {}
            text = (msg.get("content") or "").strip()
    return r.status_code, text, data if isinstance(data, dict) else None


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="писать approve/hide в БД")
    ap.add_argument(
        "--preview-api",
        action="store_true",
        help="вызвать LLM+RAG на первом батче, показать решения, БД не менять",
    )
    ap.add_argument("--batch-size", type=int, default=22, help="отзывов на один запрос к LLM")
    ap.add_argument("--max-batches", type=int, default=8, help="максимум батчей за запуск")
    ap.add_argument("--rag-top", type=int, default=4, help="сколько чанков регламента в промпт")
    ap.add_argument("--min-text", type=int, default=10, help="как в bulk: мин. длина текста")
    ap.add_argument("--min-rating", type=int, default=1, help="мин. звезда (или NULL если не --require-rating)")
    ap.add_argument("--require-rating", action="store_true")
    ap.add_argument("--source", default=None)
    ap.add_argument("--limit", type=int, default=0, help="макс. отзывов за весь запуск (0=все)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="slug модели OpenRouter")
    args = ap.parse_args()

    if args.apply and args.preview_api:
        print("Укажи только один из --apply или --preview-api", file=sys.stderr)
        return 2

    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if args.apply and not api_key:
        print("OPENROUTER_API_KEY не задан — нельзя --apply.", file=sys.stderr)
        return 1
    if args.preview_api and not api_key:
        print("OPENROUTER_API_KEY не задан — нельзя --preview-api.", file=sys.stderr)
        return 1

    if not RAG_PATH.is_file():
        print(f"Нет файла регламента: {RAG_PATH}", file=sys.stderr)
        return 2

    rag_text = RAG_PATH.read_text(encoding="utf-8")
    chunks = _split_rag_chunks(rag_text)

    con = sqlite3.connect(str(DB), timeout=120.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=600000")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where = [
        "status = 'pending'",
        "LENGTH(TRIM(COALESCE(text,''))) >= ?",
    ]
    qparams: list = [args.min_text]
    if args.source:
        where.append("source = ?")
        qparams.append(args.source.strip())
    if args.require_rating:
        where.append("rating IS NOT NULL AND rating >= ?")
        qparams.append(args.min_rating)
    else:
        where.append("(rating IS NULL OR rating >= ?)")
        qparams.append(args.min_rating)

    sql = (
        "SELECT id, spot_id, source, rating, author, text FROM banya_reviews WHERE "
        + " AND ".join(where)
        + " ORDER BY id ASC"
    )
    if args.limit and args.limit > 0:
        sql += f" LIMIT {int(args.limit)}"

    pending = cur.execute(sql, qparams).fetchall()
    if not pending:
        print("Нет кандидатов pending по фильтрам.")
        return 0

    print(f"Кандидатов pending: {len(pending)} (чанков регламента: {len(chunks)})")

    if not args.apply and not args.preview_api:
        for r in pending[:25]:
            t = (r["text"] or "")[:88]
            print(f"  #{r['id']} spot={r['spot_id']} ★{r['rating']} {t}")
        if len(pending) > 25:
            print(f"  … ещё {len(pending) - 25}")
        print(
            "\nДальше: --preview-api (пробный ответ модели, 1 батч) "
            "или --apply (запись в БД). Нужны эмбеддинги + OPENROUTER_API_KEY."
        )
        return 0

    print(f"Загрузка эмбеддингов ({EMBED_MODEL})…")
    try:
        from sentence_transformers import SentenceTransformer

        st_model = SentenceTransformer(EMBED_MODEL)
    except Exception as e:
        print(f"Не удалось загрузить sentence-transformers: {e}", file=sys.stderr)
        return 3

    chunk_embs = _encode_st(st_model, chunks)
    print(f"RAG: векторы чанков готовы ({len(chunks)} шт.)")

    max_batches = 1 if args.preview_api else args.max_batches
    total_processed = 0
    batches = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    system_base = (
        "Ты модератор отзывов о русских банях для сайта gdepar.ru. "
        "На каждый отзыв ответь строго JSON без markdown. "
        'Формат: {"decisions":[{"id":<int>,"action":"approve"|"hide","reason":"кратко по-русски"}]}. '
        "id должны совпадать с входом. Только approve или hide."
    )

    i = 0
    n = len(pending)
    while i < n and batches < max_batches:
        batch = pending[i : i + args.batch_size]
        i += len(batch)
        batches += 1

        lines = []
        for r in batch:
            tid = r["id"]
            txt = (r["text"] or "").strip().replace("\n", " ")[:650]
            stars = r["rating"] if r["rating"] is not None else "null"
            auth = (r["author"] or "")[:40]
            src = r["source"] or ""
            lines.append(
                json.dumps(
                    {"id": tid, "spot_id": r["spot_id"], "source": src, "rating": stars, "author": auth, "text": txt},
                    ensure_ascii=False,
                )
            )
        batch_blob = "\n".join(lines)
        rag_ctx = _top_chunks(batch_blob, chunk_embs, chunks, args.rag_top, st_model)

        user_msg = (
            "Фрагменты регламента (контекст):\n\n"
            + rag_ctx
            + "\n\n---\n\nОдин отзыв на строку (JSON). Реши для каждого:\n"
            + batch_blob
        )

        mode = "preview-api" if args.preview_api else "apply"
        print(f"\n--- batch #{batches} ({len(batch)} шт.) {mode} model={args.model} ---")

        status, raw, _meta = _call_openrouter(api_key, args.model, system_base, user_msg)
        if status != 200:
            print(f"OpenRouter HTTP {status}, тело: {raw[:500]}", file=sys.stderr)
            return 4

        parsed = _extract_json_object(raw)
        if not parsed or "decisions" not in parsed:
            print(f"Не разобрал JSON ответа:\n{raw[:1200]}", file=sys.stderr)
            return 5

        decisions = parsed["decisions"]
        if not isinstance(decisions, list):
            print("decisions не список", file=sys.stderr)
            return 5

        if args.preview_api:
            print(json.dumps(parsed, ensure_ascii=False, indent=2)[:8000])
            print("\n(--preview-api: в БД ничего не записано.)")
            return 0

        batch_ids = {int(r["id"]) for r in batch}
        spot_ids: set[int] = set()
        applied = 0
        for d in decisions:
            if not isinstance(d, dict):
                continue
            rid = d.get("id")
            action = (d.get("action") or "").strip().lower()
            if rid is None or int(rid) not in batch_ids:
                continue
            if action not in ("approve", "hide"):
                continue
            new_status = "approved" if action == "approve" else "hidden"
            cur.execute(
                "UPDATE banya_reviews SET status = ? WHERE id = ? AND status = 'pending'",
                (new_status, int(rid)),
            )
            if cur.rowcount:
                applied += cur.rowcount
                row = next((x for x in batch if int(x["id"]) == int(rid)), None)
                if row:
                    spot_ids.add(int(row["spot_id"]))
            reason = (d.get("reason") or "")[:120]
            print(f"  #{rid} → {new_status} ({reason})")

        for attempt in range(30):
            try:
                _refresh_counts(cur, spot_ids, now)
                con.commit()
                break
            except sqlite3.OperationalError as e:
                if "locked" not in str(e).lower() or attempt == 29:
                    raise
                time.sleep(1.5)

        print(f"  применено записей: {applied}, спотов обновлено: {len(spot_ids)}")
        total_processed += len(batch)

    print(f"\nИтого обработано строк (в батчах): {total_processed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
