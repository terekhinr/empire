# Empire Ops Studio — руководство (пилот Сад)

Личный контур автопоста: база, рубрики с политикой картинок, пачка Gemini, антидубли, ops-алерты.

**По умолчанию — тест.** В каналы ничего не уходит без `EMPIRE_PUBLISHER_LIVE=1` и режима «живой».

Старый curated-автопост Сада **поставлен на паузу** (bak + пустой schedule). Остальные каналы в `content_config` / `main.py` не трогаем.

Согласованная логика: `docs/ops_studio_decisions.md`.

---

## Куда заходить

| Где | Адрес |
|-----|--------|
| gdepar | https://gdepar.ru/admin/studio |
| neverretire | https://neverretire.ru/admin/studio |

Вход: `EMPIRE_STUDIO_TOKEN` или `BANYA_ADMIN_TOKEN`.

---

## Пилот Сад (7 дней test → live)

1. Проект **Сад** (`tg:garden`).
2. Рубрики: **stepanych** (Степаныч) и **lunar** (Луна) — вкладка «Рубрики».
3. Слоты: Вт+Сб 12:00 → stepanych; Ср+Сб 20:00 → lunar.
4. Импорт пачки Gemini на вкладке **База** → «Импорт пачки в базу».
5. Tick («Обработать наступившие») или cron: `python -m publisher tick`.
6. Картинки: `generate` через Gemini → при сбое `media/publisher/stub.jpg` + алерт `[stub]`.
7. Дубли: skip при ≥90% за 30 дней (импорт и перед постом).
8. Через 7 дней без fail → `EMPIRE_PUBLISHER_LIVE=1` + режим «живой» только для пилота.

### Формат пачки Gemini

```text
---
id: g1
rubric: stepanych
headline: Заголовок
image_prompt_en: Central Russia garden, documentary photo
---
Текст поста…

---
id: g2
rubric: lunar
headline: Другой
---
Текст…
```

Алиасы `rubric`: `степаныч`, `garden_curated`, `луна`, `kizima_lunar`.

### image_mode у рубрики

| Режим | Поведение |
|-------|-----------|
| `generate` | Gemini image → файл; сбой → stub |
| `archive_pool` | Пул `archive_dir` / media персоны |
| `fixed` | Один файл рубрики |
| `post` | `image_path` у поста |
| `none` | Только текст |

---

## Пауза старого Сада

Бэкапы: `data/publisher/backups/content_config.garden.*.bak.json`, `auto_publish.*.bak.json`.

Активно: `content_config.garden` — пустой schedule; `garden_lunar` / `garden_curated` — `enabled: false`.

Восстановление: скопировать garden-блок из bak обратно в `content_config.json` и включить рубрики в `auto_publish.json`.

---

## Env

| Переменная | Роль |
|------------|------|
| `EMPIRE_STUDIO_TOKEN` | Вход в UI |
| `EMPIRE_PUBLISHER_LIVE=1` | Разрешить живой режим |
| `TELEGRAM_TOKEN` | Публикация + алерты |
| `ADMIN_ID` | Chat для алертов |
| `GEMINI_API_KEY` | Картинки generate |
| `EMPIRE_STUDIO_IMAGE_MODEL` | Модель (иначе gemini-2.5-flash-image) |
| `OPENROUTER_API_KEY` | ИИ-фабрика текстов (вкладка ИИ) |

Cron:

```bash
cd /root/projects/empire && ./venv/bin/python -m publisher tick
```

Очередь: `data/publisher/store.json`. Stub: `media/publisher/stub.jpg`.

---

## Тесты

```bash
EMPIRE_SKIP_EMBEDDINGS=1 ./venv/bin/pytest tests/test_publisher.py -q
```
