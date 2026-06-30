# Stern (Снегири) — генерация в Gemini

## Статус

| Слот | в Empire | цель | осталось |
|------|----------|------|----------|
| 09:30 рутина | 68 | ~80 | ~12 (добьём позже) |
| 19:00 вечер | 14 | ~69 | **~55** ← сейчас |

**Следующие батчи:** `stern_08` … `stern_13` (слот 19:00, 69 тем).

## Старт в Gemini (2 сообщения)

### 1 — бут

`gemini_PASTE_MSG1_BOOT_STERN.txt`

Ждёшь: **«Принял. Жду задание stern_08_partA.»**

### 2 — первый батч

`gemini_PASTE_MSG2_STERN_FIRST_BATCH.txt` (= `batch_requests/stern_08_partA.txt`)

6 постов: выгорание, сон, срывы (STR-EV-001…006).

### 3+ — по одному файлу

```
batch_requests/stern_08_partB.txt
batch_requests/stern_09_partA.txt
…
batch_requests/stern_13_partB.txt
```

**12 файлов**, по 6 постов (последний — 3). Не копируй весь `gemini_BATCH_REQUESTS_REDO.md`.

## Формат ответа Stern

```markdown
---
id: stern_1900_ev_001_b08
slot: 1900
topic_raw: [Психология] Выгорание и дисциплина.
hashtags: #снегири #штерн #психология
image_prompt_en: office desk kettlebell soft light photorealistic no face
---

🏛️ <b>Заголовок</b>

Текст 2–4 абзаца, HTML <b>.

#снегири #штерн #психология
```

## Если Gemini обрезал

```
POST_COUNT должен быть 6. Ты дал 1 пост и «остальные в том же стиле».
Перегенерируй stern_08_partA целиком: все 6 постов, полный текст.
```

## Импорт в Empire

Сохрани ответ как `gemini-code-stern_08_partA.md` в `docs/content_factory/gemini_export/`, затем:

```bash
./venv/bin/python tools/ingest_gemini_content_export.py
```

Или вставь сюда в чат (как с Gdepar) — импортирую сам.

## P0 для Stern (брак)

- Выдуманные % и «исследования»
- >3 хэштегов
- Махи гирей / тяжёлое «всем сегодня» при боли в спине
- «Кортизол −20%», неоновый фитнес-тон

## Автопост

Слоты 09:30 и 19:00 уже на `stern_curated` (без LLM). Новые посты попадут в очередь после ingest.
