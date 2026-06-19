# Empire — правила vault (вставьте в Obsidian как Empire/README.md)

## Три места

1. **`_canvas/`** и **`_scenarios/`** — планирую, не импортируется.
2. **`inbox/`** — черновики, можно без шапки YAML.
3. **`queue/`** — готово к Telegram; один файл = один пост.

После публикации → переношу в **`published/`**.

## Pension

- Шаблон Obsidian: папка **`Empire/pension/_templates`** (файл `obsidian_pension_post.md`)
- Очередь: `Empire/pension/queue/`
- Черновики: `pension/inbox/` · архив: `pension/published/`

## Шапка файла в queue/

```yaml
---
id: уникальный-id
persona: pension
title: "Заголовок"
scheduled: "2026-06-01 11:00"
status: ready
---
```

`persona`: pension | gdepar | garden | stern | lenin

## Тело

Пишу сырой текст. Хештеги и 📌 — добавит Empire при сборке поста.

## На сервере

```bash
export OBSIDIAN_EMPIRE_INCOMING=…/Empire/pension/queue
./venv/bin/python scripts/import_obsidian_queue.py
```

Полный гайд: репозиторий Empire → `docs/obsidian_practical_guide_ru.md`  
ИИ на ПК (Geminese): `docs/obsidian_geminese_setup_ru.md`

## Два потока

- **Мой текст** → queue → импорт → бот → Опубликовать
- **Автослоты Empire** (ИИ/рубрики) → тоже в бот → Опубликовать

Не ставлю один слот и Obsidian-пост, и ИИ на одно время без решения.

## Рост без MAX (чеклисты)

- **`_scenarios/growth-rf-2026.md`** — день / неделя / месяц / полугодие / год (галочки `- [ ]`)
- Шаблон дневной заметки: `templates/obsidian_growth_daily_note.md` → в Obsidian Templates
- **Еженедельный review:** `templates/weekly_project_review.md` → `Empire/_reviews/` (после KPI в дашборде)
- Стратегия: `docs/growth_rf_no_max_2026.md` · правила: `docs/PROJECT_OS.md`
