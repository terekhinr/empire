# NotebookLM · промпты по каналам Empire

**Дата:** 2026-07-23

## Порядок

1. Гдепар — `prompt_gdepar.txt`
2. Снегири — `prompt_snegiri.txt`
3. Сад — `prompt_sad.txt`
4. **Ленин** — `prompt_lenin.txt` (cinema / monument / bedtime; календарь — Empire)

## Ленин · ingest

Пачки Архивариуса:

```bash
./venv/bin/python scripts/ingest_lenin_archivist_batch.py \
  docs/content_factory/generated/lenin_archivist_batch_YYYY-MM-DD.md
```

Сетка: `docs/content_factory/LENIN_SCHEDULE_2026-07-22.md`
