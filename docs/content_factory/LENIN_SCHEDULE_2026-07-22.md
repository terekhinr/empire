# Ленин · сетка и NotebookLM (2026-07-22)

**Голос:** Архивариус. **Автопост:** `enabled=false` (черновик → Publish).

## Расписание

| День | 08:30 | 12:00 | 19:00 |
|------|-------|-------|-------|
| Пн–Пт | `lenin_calendar` | `lenin_rubric` | ПСС ↔ книга |
| **Сб** | календарь | рубрика | **`lenin_book` = сказка на ночь** |
| Вс | календарь | рубрика | `channel_support` |

## Календарь

Источник: `data/lenin/revolutionary_calendar.txt`. Формат не менять.

## Промпт NL

[`notebooklm_dlya_tebya/prompt_lenin.txt`](notebooklm_dlya_tebya/prompt_lenin.txt)

Режимы: **cinema** · **monument** · **bedtime**.

## Ingest пачек Архивариуса

```bash
./venv/bin/python scripts/ingest_lenin_archivist_batch.py \
  docs/content_factory/generated/lenin_archivist_batch_YYYY-MM-DD.md
```

Пишет в `data/lenin_rubrics.json` (cinema/art/literature) и `data/lenin_bedtime_stories.json`.
