# Empire — общий пайплайн и чеклисты

**Обновлено:** 2026-06-01  
**Зачем один файл:** видеть **что сделано / что осталось** по двум продуктовым линиям — **Pension** (neverretire.ru, YouTube) и **gdepar** (карта бань, «Пар?»), плюс общая инфраструктура.

Статусы: `⬜` не начато · `🔄` в работе · `✅` готово · `⏸` ждёт вас (внешний сервис / ключ)

---

## Общая инфраструктура Empire

| # | Задача | Статус | Как проверить |
|---|--------|--------|----------------|
| I1 | VPS / `empire_gdepar` / `empire` сервисы живы | 🔄 | `curl -s https://gdepar.ru/api/gdepar/health` |
| I2 | OpenRouter ключ в env (gdepar assistant + генерация) | ⬜ | health → `assistant` / логи без 401 |
| I3 | Obsidian vault синхрон с `data/obsidian_vault/Empire/` | 🔄 | посты в `pension/queue/` |
| I4 | Еженедельные метрики Pension | ⬜ | `data/pension_weekly_metrics.json` |
| I5 | Финансы P&L | ⬜ | `data/empire_finance_ledger.json` |

---

## Блок A — Pension · «На пенсию НИКОГДА»

**Сайт:** https://neverretire.ru · **Книга:** `data/pension/book_complete (1).md`  
**Дорожная карта YT:** `docs/pension_youtube_roadmap_12m_2026.md` · **Запуск YT:** `docs/pension_youtube_launch_guide.md`

### A1. Контент и знания (сделано / в работе)

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| A1.1 | Черновик книги (7666 строк) | ✅ | |
| A1.2 | Кримсон в `kb_sources/pension/crimson/` (24 файла) | ✅ | PDF + mhtml «Индексные фонды» |
| A1.3 | RAG pension переиндексирован (только `kb_sources/pension`, 6428 чанков) | ✅ | без `scripts/` и `reference/` |
| A1.4 | Эталоны Мячина в `data/pension/scripts/myachin/` | ✅ | 2 PDF-сценария |
| A1.5 | Книги-источники в `data/pension/reference/books/` | ✅ | Марков, Талеб — **не** в RAG постов |
| A1.6 | Справочник формата Мячина | ✅ | `docs/pension_reference_myachin.md` |
| A1.7 | Шаблоны сценариев YT | ✅ | `data/pension/scripts/` |
| A1.8 | Пример сценария YT №1 (Понци) | ✅ | `data/pension/scripts/pension_yt/yt-001_pension_ponzi.md` |
| A1.9 | Очередь лонгридов Obsidian | 🔄 | `data/obsidian_vault/Empire/pension/queue/` |
| A1.10 | Контент-календарь 12 нед | ✅ | `docs/pension_content_calendar_2026.md` |
| A1.11 | Лонгриды Дзен/VK (5 шт.) | ✅ | `data/pension/longreads/` |

### A2. Сайт neverretire.ru

| # | Задача | Статус | Документ |
|---|--------|--------|----------|
| A2.1 | Сайт опубликован, разделы книга/разборы | ✅ | |
| A2.2 | **Яндекс.Метрика** — отдельный счётчик | ⏸ | `docs/pension_analytics_accounts_guide.md` |
| A2.3 | Цели Метрики (email, book, youtube UTM) | ⏸ | `docs/pension_book_publish_tz.md` §6 |
| A2.4 | PDF книги + `/buy` | 🔄 | `docs/pension_book_publish_tz.md` |
| A2.5 | Email pre-launch база | ⬜ | цель ≥50 к августу 2026 |

### A3. YouTube «Иосиф Борода» / @neverretire

| # | Задача | Статус | Неделя |
|---|--------|--------|--------|
| A3.1 | Google-аккаунт + канал + оформление | ⬜ | 1 |
| A3.2 | Шаблон превью + дисклеймер ИИР | ⬜ | 1 |
| A3.3 | Выпуск №1 снят (сценарий yt-001) | ⬜ | 1–2 |
| A3.4 | 12 роликов без пропуска >2 нед | ⬜ | Q1 2026 |
| A3.5 | Дзен из сценариев (раз в 2 нед) | ⬜ | с нед. 3 |
| A3.6 | Launch книги | ⬜ | октябрь 2026 |

### A4. Пайплайн контента Pension (одна строка)

```
Книга / Crimson RAG + новость дашборда
  → сценарий YT (шаблон Мячина) → съёмка → YT
  → нарезка лонгрида Дзен + пост TG + карточка neverretire.ru
```

**Команды:**

```bash
# RAG только kb_sources (Кримсон + mhtml), без scripts/reference
cd /root/projects/empire
./venv/bin/python tools/build_rag.py --persona pension --force \
  --input-dir kb_sources/pension

# Проверка индекса
test -f data/rag_manifest_pension.json && cat data/rag_manifest_pension.json
```

---

## Блок B — gdepar.ru · «Пар?»

**Сайт:** https://gdepar.ru · **ТЗ помощника:** `docs/gdepar_ai_assistant_tz.md`  
**Статус выката:** `docs/gdepar_checkpoints.md` (CP-20260520)

### B1. Техника (сделано агентом)

| # | Задача | Статус |
|---|--------|--------|
| B1.1 | Помощник «Пар?», SSE, кэш, RL | ✅ |
| B1.2 | `GET /api/gdepar/health` | ✅ |
| B1.3 | LLM rollout `GDEPAR_ASSISTANT_LLM_PCT=25` | ✅ |
| B1.4 | Код целей Метрики в шаблонах | ✅ |

### B2. Только владелец

| # | Задача | Статус | Действие |
|---|--------|--------|----------|
| B2.1 | Создать счётчик Метрики | ⏸ | metrika.yandex.ru |
| B2.2 | `YANDEX_METRIKA_ID` в `/etc/empire/gdepar.env` | ⏸ | + `systemctl restart empire_gdepar` |
| B2.3 | JS-цели в кабинете | ⏸ | `docs/metrika_goals_setup.md` |
| B2.4 | Неделя 1: «Пар?», стриминг, OpenRouter | ⬜ | после B2.2 |
| B2.5 | 2–4 нед: решение по `GDEPAR_ASSISTANT_LLM_PCT` | ⬜ | 25 / 50–100 / 0 |
| B2.6 | Мастер-ТЗ империи | ⬜ | `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md` |

### B3. Пайплайн gdepar

```
Посетитель → gdepar.ru → Метрика
  → «Пар?» → submit → pick / phone (CR1)
  → (опц.) саммари попапа
```

**Проверка:**

```bash
curl -s https://gdepar.ru/api/gdepar/health | python3 -m json.tool
journalctl -u empire_gdepar | grep 'timing route='   # если тормозит
```

---

## Блок C — Формат «как у Мячина» (общий для Pension YT)

| Вариант | Когда | Старт | Артефакт |
|---------|-------|-------|----------|
| **C1 Сценарий → видео** (основной) | Evergreen, 15–25 мин | Книга + цифры | `.md` в `scripts/pension_yt/` |
| **C2 Лонгрид → расширение** | Новость недели | Obsidian queue | пост → +10 мин в сценарий |
| **C3 Книга → серия** | 22 главы | Оглавление книги | 1–2 ролика на главу |

Детали: `docs/pension_reference_myachin.md` · шаблон: `data/pension/scripts/_template_myachin_script.md`

---

## Сводка «что сделать в первую очередь»

1. **Pension:** дождаться/завершить RAG Crimson → снять yt-001 по готовому сценарию → Metrika neverretire (отдельно от gdepar).
2. **gdepar:** Metrika ID + цели → проверить «Пар?» → через 2–4 недели LLM_PCT.

---

## Связанные файлы

| Файл | Содержание |
|------|------------|
| `docs/REMINDERS_gdepar.md` | Короткая выжимка B2 (календарь) |
| `docs/pension_reference_myachin.md` | PDF↔YT, структура блоков |
| `docs/pension_content_calendar_2026.md` | 12 нед + год |
| `kb_sources/pension/README.md` | Как класть Crimson |
| `data/pension/scripts/README.md` | Папки scripts / reference |
