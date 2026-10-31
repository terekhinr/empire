# Empire — общий пайплайн и чеклисты

**Обновлено:** 2026-09-06 (R6 dual-flagship)  
**Зачем один файл:** видеть **что сделано / что осталось** по двум продуктовым линиям — **Pension** (neverretire.ru, YouTube) и **gdepar** (карта бань, «Пар?»), плюс **omni-publish** (5 TG) и инфраструктура.

**Ревизия R5:** `docs/audit/14_PIPELINE_R5_AUTOPOST.md`  
**Ревизия R6 (факты + деньги + 90 дней):** `docs/audit/15_FINANCIAL_MODEL_R6_2026-09-05.md` · `docs/audit/17_MILESTONES_R6_90D.md` · `docs/audit/18_GDEPAR_CONTENT_MONEY_R6.md` · промпт Gemini `docs/audit/16_GEMINI_PROMPT_DUAL_FLAGSHIP_R6.md`

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
| I6 | **Автопост 5 TG** (`auto_publish.json`) | ✅ | `journalctl -u empire \| grep autopublish` |
| I7 | **KPI недели** (вкл. автопост + email) | ⬜ | `data/empire_weekly_kpi.json` · шаблон CSV |
| I8 | Метрика **оба** сайта | ⏸ | gdepar + neverretire — блокер воронки |
| I9 | **DR: docs/infra + Я.Диск** | ✅ | `docs/infra/README.md` · `vps_restore_from_yandex.sh` |

---

## Блок D — Omni-publish · все TG

**Док:** `docs/empire_autopost_strategy_2026.md` · **Ритуал:** ежедневно ~15 мин.

```
content/*/queue + рубрики JSON
  → auto_publish.json (слоты по persona)
  → 5 TG: gdepar, pension, stern, lenin, garden
  → CTA UTM → neverretire.ru / gdepar.ru
  → KPI: tg_posts_published, autopost_failures (еженедельно)
```

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| D1 | Слоты всех 5 персон в `auto_publish.json` | ✅ | июнь 26 |
| D2 | Curated-рубрики (gdepar, stern, lenin) | ✅ | `activate_curated_rubrics.sh` |
| D3 | Подпитка queue (Obsidian → content) | 🔄 | не допускать пустых слотов |
| D4 | `views_24h` в analytics.db | ⬜ | бэклог август |
| D5 | Частота постов по данным | ⬜ | после 4–6 нед логов |

**Не делать:** добавлять слоты >5/день на «медленных» каналах без A/B.

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
| A2.5 | Email pre-launch база | ⬜ | **R6:** ≥40 к 31.10, ≥50 к 30.11 (август сорван, waitlist=0) |
| A2.6 | TG→сайт дедуп + RSS timer | ✅ | `pension_site_sync` · `empire-pension-site-sync.timer` |

### A3. YouTube «Иосиф Борода» / @neverretire

| # | Задача | Статус | Неделя |
|---|--------|--------|--------|
| A3.1 | Google-аккаунт + канал + оформление | ⬜ | 1 |
| A3.2 | Шаблон превью + дисклеймер ИИР | ⬜ | 1 |
| A3.3 | Выпуск №1 снят (сценарий yt-001) | ⬜ | 1–2 |
| A3.4 | 12 роликов без пропуска >2 нед | ⬜ | Q1 2026 |
| A3.5 | Дзен из сценариев (раз в 2 нед) | ⬜ | с нед. 3 |
| A3.6 | Launch книги **299 ₽** | ⬜ | **R6 soft delay → 01.11.2026** (не 15.09) |
| A3.7 | Pre-sale **149 ₽** | ⬜ | **R6:** октябрь soft sale, цель 5–10 |
| A3.8 | YT №1–2 | ⬜ | **R6:** публикация до **15.10.2026** (август/1 сен сорваны) |

### A4. Пайплайн контента Pension (одна строка)

```
Книга / Crimson RAG + новость дашборда
  → сценарий YT (шаблон Мячина) → съёмка → YT (с 1 сен)
  → автопост TG Pension + спутники (CTA /book, /gift)
  → нарезка лонгрида Дзен (после финала книги)
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

## Сводка «что сделать в первую очередь» (сентябрь 26, R6)

1. **Метрика** — оба счётчика (без этого KPI слепые) — всё ещё блокер.
2. **Pension:** не форсировать launch 15.09 → PDF+оплата+email+YT к **01.11**; Obsidian queue (18 файлов) → TG ≥2/нед.
3. **gdepar:** Metrika + UTM-гиды 1×/нед + phone enrich MSK; карта 2045 уже ок.
4. **Omni-publish:** pension persona **оставить disabled**; классика/curated — да.
5. **Деньги:** вести ledger; bridge 35k не жечь на Директ без Metrika.
6. Календарь 90 дней: `docs/audit/17_MILESTONES_R6_90D.md`.

---

## Связанные файлы

| Файл | Содержание |
|------|------------|
| `docs/REMINDERS_gdepar.md` | Короткая выжимка B2 (календарь) |
| `docs/pension_reference_myachin.md` | PDF↔YT, структура блоков |
| `docs/pension_content_calendar_2026.md` | 12 нед + год |
| `kb_sources/pension/README.md` | Как класть Crimson |
| `data/pension/scripts/README.md` | Папки scripts / reference |
| `docs/audit/14_PIPELINE_R5_AUTOPOST.md` | R5: автопост, метрики, сроки |
| `docs/empire_kpi_sheets_template.md` | Колонки KPI + пороги |
| `docs/infra/README.md` | Сеть Flint, VPS runbook, бэкап/restore Я.Диск |
| `docs/YANDEX_RCLONE_START.md` | rclone + Яндекс (старт) |
