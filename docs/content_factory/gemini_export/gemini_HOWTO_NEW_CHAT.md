# Gemini — без зависаний

## Почему виснет

1. **Gemini не распаковывает** `.tar` / `.tar.gz` — просит фазу 0 и стоит.
2. **Старый** `gemini_PASTE_FIRST.txt` — тянет архив + фазу 0.
3. **Огромная вставка** — весь `gemini_BATCH_REQUESTS_REDO.md` (3800+ строк) перегружает чат.

## Правильный старт (2 сообщения)

### Сообщение 1

Скопируй **целиком** → `gemini_PASTE_MSG1_BOOT.txt`

- Без файлов, без архива.
- Gemini ответит: «Принял. Жду задание gdepar_02_partA.»

### Сообщение 2

Скопируй → `gemini_PASTE_MSG2_FIRST_BATCH.txt`

- 6 постов Gdepar, короткое задание.
- Ответ сохрани как `gemini-code-*.md` в `docs/content_factory/gemini_export/`

### Сообщения 3+

По **одному** файлу из `batch_requests/`:

- `gdepar_02_partB.txt`
- `gdepar_03_partA.txt`
- … и т.д.

**Не копируй** весь `gemini_BATCH_REQUESTS_REDO.md`.

## Если снова обрезал

```
POST_COUNT должен быть 6. Ты дал 1 пост и «остальные в том же стиле».
Перегенерируй gdepar_02_partA целиком: все 6 постов, полный текст.
```

## Импорт в Empire

```bash
./venv/bin/python tools/ingest_gemini_content_export.py
```

## Импорт из Gemini Share

Чат с постами: https://share.gemini.google/hLl6LaMg9e0X

Скопируй ответы в `gemini-code-*.md` → см. **`gemini_IMPORT_FROM_SHARE.md`**

## Stern (Снегири)

См. **`gemini_HOWTO_STERN.md`** — бут `gemini_PASTE_MSG1_BOOT_STERN.txt`, батчи `stern_08`…`stern_13`.

---

```bash
./venv/bin/python tools/build_gemini_batch_requests.py
```
