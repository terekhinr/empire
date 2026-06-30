# Формат импорта Gdepar → Empire

После фазы QUALITY (вердикт ПУБЛИКОВАТЬ) собери посты в один markdown:

**Файл назначения:** `gdepar_duo_curated_import_raw.md`

## Шаблон одного поста

```markdown
---
id: duo_unique_slug
pool: practice
tag: психология
headline: Заголовок без эмодзи
hashtags: #баня #гдепар #психология
image_file: null
---

🔥 **Заголовок**

**Михалыч:** …

**Кириллыч:** …
```

## Правила id
- Уникальный slug: `duo_venik_birch_02`, не совпадать с `EXISTING_gdepar_duo.json`.
- pool: `practice` | `evening` | `banya_week`

## banya_week
В конце поста одна строка URL (владелец подставит slug):
`https://gdepar.ru/banya/SLUG?utm_source=telegram&utm_medium=post&utm_campaign=banya_week`

Цитата отзыва — только если дана в задании батча.

## Сборка на сервере

```bash
./venv/bin/python scripts/parse_gdepar_duo_import.py
```

## Именование файлов от Gemini

`gdepar_batch_01_import.md`, `gdepar_batch_02_import.md`, …
