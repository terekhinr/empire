# Личный Практикум · B2B Python Developer

**Версия:** 3.0 · **2026-10-22** (LMS с нуля: Codecademy UX + Практикум/Gemini контент)  
**Идеология:** **30% теория** (Stepik/docs) · **70% практика** (VS Code + ИИ-ментор, не копипаста).  
**Семестр 1:** 17 недель (W0–W16) при **3–4 ч/день** на B2B-блок (в deep work 20–24 ч/нед вместе с медиа).  
**Не путать** с «9 свободных часов хаоса» — потолок deep work жёсткий.

**Живой курс в браузере:** https://neverretire.ru/go-learn/  
(Continue · % · недельный силлабус · галочки без SPA)

**UX-якорь:** [Codecademy / Baymard Online Learning top](https://baymard.com/ux-benchmark/collections/online-learning) — path → week/lesson → steps, прогресс по уроку, «продолжить с места».  
**Контент-якорь:** Яндекс Практикум + предложение Gemini «Личный Практикум» (модули, критерии, PAUSE).

| Канон | Путь |
|-------|------|
| Паузы / КТ / HOME | [`career_12m_calendar_pauses_2026-10.md`](career_12m_calendar_pauses_2026-10.md) |
| Стендапы | [`tracker/DAILY_STANDUP.md`](tracker/DAILY_STANDUP.md) · [`tracker/WEEKLY_SPRINT.md`](tracker/WEEKLY_SPRINT.md) |
| Продукт Lead Bot | [`career_tz_b2b_lead_bot_2026-10.md`](career_tz_b2b_lead_bot_2026-10.md) |
| ИИ-ментор | `.cursor/rules/career-practicum-mentor.mdc` · `.clinerules` |
| LMS seed | `scripts/seed_practicum_lms_2026.py --force` |
| Входы | `/go/` · `/go-tasks/` · `/gym/` · `/go-learn/` |

Платный Яндекс Практикум **не обязателен** — это самостоятельный аналог.

---

## Карта семестра 1 → календарь Empire

| Модуль Практикума | Недели | ~Календарь | Выход | КТ |
|-------------------|--------|------------|-------|-----|
| Онбординг | 0 | M0 | режим, репо, ментор | КТ-0 |
| **1. Python + Git** | 1–4 | M0–M1 | консольный To-Do | |
| **2. Aiogram + FSM** | 5–8 | M1–M2 | echo + анкета → консоль | → КТ-1* |
| **3. SQL + ORM** | 9–12 | M2–M4 | анкета пишет в БД | КТ-1 |
| **4. Docker + Sheets + деплой** | 13–16 | M5–M6 | **диплом = Lead Bot** | → КТ-2 |
| Семестр 2 (рынок) | после | M7–M11 | Alembic polish, кейсы, CustDev | КТ-3…4 |

\*После модуля 2 уже есть FSM; **КТ-1** формально при памяти в БД (конец модуля 3).

При **PAUSE:** Stepik/SQL/Mastergroosha текстом + стендап; без Docker/VPS/4K.

---

## Ритуалы

### Ежедневно (~10 мин вечером)

1. Блок А (B2B) / Б / В по факту дня.  
2. Запись в [`tracker/DAILY_STANDUP.md`](tracker/DAILY_STANDUP.md) **и** чеклист «Ежедневный отчёт» в PWA.  
3. EN 30 мин (можно вложить в прогулку).

### Воскресенье · спринт-ревью

[`tracker/WEEKLY_SPRINT.md`](tracker/WEEKLY_SPRINT.md): сделано/провалено · что не понимаю · одна цель на 7 дней.

### ИИ как преподаватель

Правила ментора — не писать готовый код. Скелет с `# ТУТ ТВОЙ КОД` + наводящий вопрос.

---

## Модуль 1 · Базовый Python и алгоритмика (недели 1–4)

**Темы:** переменные, типы, `for`/`while`, `if`, функции, списки/словари, Git (коммиты, ветки).

**Ресурсы:**
- [Stepik · Поколение Python: курс для начинающих](https://stepik.org/course/58852/) — якорь; удобно в PAUSE/телефон  
- [Официальный Tutorial Python](https://docs.python.org/3/tutorial/)  
- Git: [Pro Git · Basics](https://git-scm.com/book/ru/v2)

**Проект модуля:** консольный **To-Do** (терминал), задачи в `.txt` или `.json`.  
Репо: `b2b_lead_bot/sandbox/todo_cli/` (или отдельная папка `sandbox/`).

**Критерий:** To-Do add/list/done работает; ≥5 понятных git-коммитов; объясняешь словарь без подсказки.

---

## Модуль 2 · Telegram-боты и асинхронность (недели 5–8)

**Темы:** API, webhook vs long-polling, `async`/`await`, aiogram 3, FSM (анкета).

**Ресурсы:**
- [Mastergroosha · Пишем Telegram-ботов с aiogram 3.x](https://mastergroosha.github.io/aiogram-3-guide/) ← главный учебник РФ  
- [Quickstart](https://mastergroosha.github.io/aiogram-3-guide/quickstart/) · [FSM](https://mastergroosha.github.io/aiogram-3-guide/fsm/)  
- [Документация aiogram 3](https://docs.aiogram.dev/en/latest/)

**Проект модуля:** учебный **эхо-бот** + **бот-анкета** (имя, телефон, запрос → вывод в консоль/лог). Пока без БД.

**Критерий:** `/cancel` сбрасывает FSM; polling vs webhook — одним абзацем; код объясним.

---

## Модуль 3 · Базы данных, SQL и ORM (недели 9–12)

**Темы:** SQLite/PostgreSQL, `SELECT`/`INSERT`/`JOIN`, SQLAlchemy 2.0, введение в Alembic.

**Ресурсы:**
- [Stepik · Интерактивный тренажёр SQL](https://stepik.org/course/63054/)  
- [SQL Academy](https://sql-academy.org/)  
- [SQLAlchemy 2.0 ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)  
- YouTube: плейлисты по SQLAlchemy 2.0 (напр. канал **Артём Шумейко**) — смотреть 1 ролик → сразу практика  
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)

**Проект модуля:** анкета **пишет в SQLite**, затем тот же schema на Postgres. Бот помнит обратившихся.

**Критерий = КТ-1:** рестарт не убивает данные; модель `leads`; голосом объясняешь схему.

---

## Модуль 4 · Инфраструктура, API и деплой (недели 13–16) — диплом

**Темы:** Docker / Compose, Google Sheets API (сервисный аккаунт), `logging`, деплой на VPS (руками).

**Ресурсы:**
- [Docker Get Started](https://docs.docker.com/get-started/)  
- Stepik: курс «Docker для начинающих» (поиск на stepik.org; + официальные доки как якорь)  
- [Compose file](https://docs.docker.com/compose/compose-file/)  
- [Google Sheets API concepts](https://developers.google.com/sheets/api/guides/concepts)  
- [Sheets Python quickstart](https://developers.google.com/sheets/api/quickstart/python)  
- [Logging HOWTO](https://docs.python.org/3/howto/logging.html)

**Проект модуля (диплом):** **B2B Lead Bot** — Docker, PostgreSQL, дубль в Google Sheet, логи ошибок, работа на VPS.  
Структура — как в `career_tz_b2b_lead_bot_2026-10.md`.

**Критерий = КТ-2:** `clone → .env → compose up` → полный лид; README ≤5 команд; демо 5 мин.

Alembic «взрослый» + полировка админки — сразу после диплома (календарь M7–M8), не обязателен внутри недели 16, если буфер PAUSE.

---

## Семестр 2 (после диплома) — кратко

| Фокус | КТ |
|-------|-----|
| Alembic status, админ-кнопки, VPS-прогон | |
| Устойчивость integrations + 2-й кейс README | → КТ-3 |
| 15 агентств, CustDev только боли, EN pitch | КТ-3 |
| Go/no-go, подушка, юрконтур | КТ-4 |
| D-day | уход |

Автоканалы — только автопост. Полка закрыта.

---

## Параллельно · English + Медиа

| Блок | ч/нед | Содержание |
|------|------:|------------|
| EN | ~3 | docs модуля + Anki ([ankiweb](https://apps.ankiweb.net/)) |
| Пенсия (Блок Б) | 6–7 | книга / ролик |
| Где Пар (Блок В) | 2–3 | Метрика, воронка |

---

## Соответствие Яндекс Практикуму

| Практикум | Личный Практикум Empire |
|-----------|-------------------------|
| Спринт | Неделя + воскресное ревью |
| Тренажёр | Stepik 58852 / 63054 |
| Проект модуля | To-Do → анкета → БД → Lead Bot |
| Ментор | Cursor/Roo по правилам ментора |
| Диплом | B2B Lead Bot (модуль 4) |
| Карьерный центр | Семестр 2 · рынок без оплаты до ухода |

---

## Seed / чеклисты

После `scripts/seed_career_b2b_plan_2026.py --force`:

- `Карьера · Sem1 · Модуль 1…4`  
- фазы S0–S7  
- ежедневный стендап / воскресный review / PAUSE  
