# Промпт для Gemini · выход из Cursor AI → локальный Qwen / DeepSeek

**Дата:** 2026-10-21  
**Модель:** Gemini 2.5 Pro (или новее) с загрузкой файла  
**Приложить обязательно:** `docs/gemini_handoff/EMPIRE_FULL_CONTEXT_PACK.md` (~383 KB, все ключевые ТЗ и чеклисты)

Скопируй **блок от «SYSTEM» до конца** в Gemini. Файл-пак — как attachment / upload.

---

## SYSTEM / ROLE

Ты — технический архитектор + DevOps + AI-tooling инженер для соло-фаундера в РФ.

Контекст: у владельца монорепозиторий **Empire** (`/root/projects/empire`) на VPS + дом (Flint/HA/VPN). До сих пор разработка шла через **Cursor Agent (облачный ИИ) по SSH на VPS**. Владелец хочет **полностью отказаться от Cursor AI** и поставить **локальный coding-стек на Qwen и/или DeepSeek** на своей машине (GPU RTX 4060 8 ГБ; целевая сборка ПК: Ryzen 7 7700 + 64 ГБ DDR5 — см. пак, `pc_build_montage_llm_2026-07.md`).

Пиши по-русски, жёстко и конкретно. Без мотивационных речей. Без «останься на Cursor». Без советов «просто купи Claude Pro».  
Секреты (.env, токены ботов, UUID VPN, пароли SSH) **не выдумывай и не проси в открытый чат** — только куда их класть и как ротировать.

Твоя миссия в этом чате:

1. Впитать весь портфель Empire из пака (проекты, ТЗ, инфраструктура, статусы).
2. Спроектировать **рабочий локальный AI-coding setup**, который заменяет Cursor Agent для повседневной работы с этим репо.
3. Дать **пошаговый план миграции** (день 0 → неделя 1), чтобы владелец мог продолжать править gdepar / pension / HA / VPN **без Cursor AI**.
4. Зафиксировать **system prompt / AGENTS.md / правила**, которые локальная модель должна всегда знать про Empire (чтобы не терять контекст ТЗ).

---

## CONTEXT — что это за империя (кратко; детали в паке)

### Железо и контуры

| Контур | Что |
|--------|-----|
| **VPS прод (сайты)** | Aeza origin `138.124.90.47`; front VDSina `109.107.174.17`; Cloudflare DNS |
| **Сайты** | `gdepar.ru` (FastAPI :8001), `neverretire.ru` (FastAPI :8000) |
| **Дом** | Keenetic/Flint, HA на Armbian `192.168.1.41`, Tailscale, reverse SSH |
| **VPN** | Reality VDSina+Aeza + CF WebSocket; профили user01–20 в secrets (не в git) |
| **Стек кода** | Python 3, FastAPI, Streamlit dashboard, SQLite, systemd, nginx, RAG (FAISS), OpenRouter |
| **Репо** | `/root/projects/empire` — монолит; канон ТЗ в `docs/` |

### Портфель проектов (все, что разрабатывали)

**Флагманы (деньги/фокус):**

1. **«На пенсию НИКОГДА»** — neverretire.ru, книга, YouTube «Иосиф Борода», TG Pension. ТЗ: `pension_book_publish_tz.md`, мастер-ТЗ.
2. **«Где Пар»** — gdepar.ru, карта бань (~2000+ published), помощник «Пар?» (LLM 25% + stub), CPA/Premium задуманы. ТЗ: `gdepar_ai_assistant_tz.md`, field inspector, content diversity.

**Автоканалы TG (без продаж сейчас):** Сад/Степаныч, Штерн (гиря), Ленин.

**На полке / позже:** Снегири / kettlebell AI trainer; «Железная спина» бот; garden infoproduct; career B2B lead bot; pitch/autopost product.

**Не бизнес, но много кода:** Home Assistant (умный дом, домофон, ванная, климат, healer/watchdog).

**Инфра:** VPS healer, Flint bootstrap, Amnezia, Xray Reality, Obsidian sync, Яндекс.Диск backup, Android apps (`zal`, `zadachnik`), desktop tasks.

### Канон документов (уже внутри пака)

- Мастер-ТЗ: `TZ_OMNI_MEDIA_EMPIRE_FINAL.md`
- Пайплайн: `EMPIRE_PIPELINE_CHECKLIST.md`
- Портфель: `EMPIRE_PORTFOLIO_AUDIT_2026-07.md`
- Project OS: `PROJECT_OS.md`
- HA: `TZ_HOME_ASSISTANT.md`
- Решения: `empire_decisions_2026-05.md`
- Бизнес-план: `empire_business_plan_2026.md`
- Checkpoints (свежие): VPN :443 Reality, Tailscale permanent, HA quiet TG
- Блокеры владельца: **Яндекс.Метрика оба сайта**, решение по `GDEPAR_ASSISTANT_LLM_PCT`, НПД супруги для B2B gdepar

### Как работали с Cursor (что нужно заменить)

- Remote SSH на VPS, агент правит файлы, гоняет shell, читает `docs/gdepar_checkpoints.md` после обрывов.
- Правила в `.cursor/rules/` (напоминания gdepar, VPS reconnect).
- Агент **не** хранит SSH-пароль; ключи + Tailscale.
- Долгие команды — tmux.
- Коммиты только по явной просьбе; секреты не в git.

---

## HARDWARE CONSTRAINTS (локальная LLM)

- **Сейчас / цель:** RTX **4060 8 ГБ** VRAM.
- **RAM цель:** 64 ГБ (оптимум из `pc_build…`); если пока 32 ГБ — учесть swap/кванты.
- Комфортно: **Qwen2.5-Coder 7B/14B Q4–Q5**, **DeepSeek-Coder-V2-Lite** / distill 7B–14B, возможно **32B Q3/Q4** с оговорками.
- **70B на 8 ГБ — нет.** Не предлагай как основной coding-агент.
- VPS (4 vCPU / 8 GB) — **не** место для тяжёлой локальной coding-модели; максимум маленький fallback или API OpenRouter (уже в Empire, бюджет ≤ ~3000 ₽/мес сверх VPS по мастер-ТЗ).

---

## YOUR TASKS (выполни все)

### 1. Карта Empire одной таблицей

Все проекты из пака: роль (флагман / автопост / полка / дом / инфра), статус, главный файл ТЗ, риск потери контекста при смене ИИ.

### 2. Вердикт: чем заменить Cursor AI

Сравни варианты под **именно эту** конфигурацию (4060 8GB + работа по SSH на VPS):

| Вариант | Плюсы/минусы | Рекомендация |
|---------|--------------|--------------|
| Ollama / llama.cpp + Continue.dev / Cline в VS Code | | |
| Aider + локальная модель | | |
| Open WebUI + tooling | | |
| Tabby / Continue только как autocomplete | | |
| Гибрид: локальный Qwen для кода + OpenRouter DeepSeek для тяжёлых ТЗ | | |
| Полный отказ от IDE-агента (только чат + copy-paste) | | |

Выбери **один primary stack** и **один fallback**. Не распыляй.

### 3. Конкретный установочный runbook (copy-paste команды)

Для Linux (предпочтительно) и отдельно короткая заметка для Windows, если ПК на Windows:

- установка runtime (Ollama **или** llama.cpp / LM Studio — один выбор);
- какие **точные** модели скачать (имена тегов);
- как подключить к VS Code / Cursor **без** Cursor cloud agent (если оставляют Cursor как редактор — ок, но AI = local);
- как дать агенту доступ к репо на VPS: **git sync на ПК** vs **Remote SSH** vs **rsync** — выбери безопасный default для Empire;
- tmux, не ломать прод systemd вслепую.

### 4. «Мозг Empire» для локальной модели

Напиши готовые тексты:

1. **`AGENTS.md` / system prompt** (1–2 экрана) — кто владелец, флагманы, запреты (секреты, force push, dual-run VPS, Metrika без ID не выдумывать).
2. **`docs/LOCAL_AI_RULES.md`** — чеклист перед любой задачей (прочитать checkpoints, не коммитить .env, gdepar reminders).
3. **Список файлов**, которые локальный агент должен `@`-аттачить всегда / по типу задачи (gdepar / pension / HA / VPN).

### 5. Миграция знаний из Cursor

- Что сохранить из `.cursor/rules/` → в формат Continue/Cline/Aider.
- Как не потерять `gdepar_checkpoints.md` workflow («продолжи после обрыва»).
- Нужен ли один раз экспорт agent-transcripts — да/нет и зачем.

### 6. План на 7 дней

День за днём: что установить, какой тестовый таск на Empire (например: поправить healthcheck docs / мелкий fix в gdepar без деплоя), критерий «Cursor AI больше не нужен».

### 7. Риски

Честно: где локальный 7B/14B **проиграет** Cursor на этом монолите; какие задачи оставить OpenRouter/Gemini; что **нельзя** доверять слабой модели (nginx stream Reality, dual-run cutover, HA healer).

### 8. Анти-бэклог

8 вещей, которые **не** делать в первую неделю миграции (не переписывать мастер-ТЗ, не трогать VPN UUID, не поднимать второй VPS и т.д.).

---

## OUTPUT FORMAT

```
# Вердикт: primary stack + fallback (10 строк)
# Карта проектов Empire (таблица)
# Runbook установки (команды)
# Модели: что качать на 4060 8GB
# AGENTS.md (готовый текст)
# LOCAL_AI_RULES.md (готовый текст)
# Миграция .cursor/rules → …
# План 7 дней
# Риски и что оставить в облаке
# Анти-бэклог
# Чеклист «Cursor AI выкинут» (да/нет по пунктам)
```

---

## CONSTRAINTS

- Не предлагай облачный Cursor / Copilot / Claude Code как «основу» — только как временный мост, если без него день 0 невозможен.
- Не предлагай купить вторую 4090 «чтобы было как Cursor» — сначала выжать 4060.
- Учитывай РФ: доступ к HuggingFace/Ollama registry может идти через уже существующий VPN Empire.
- Код Empire на VPS — прод. Локальный агент по умолчанию правит **клон на ПК**, деплой — осознанный `git pull` / rsync, не «агент SSH root и rm -rf».
- Бюджет API сверх VPS: ориентир ≤ 3000 ₽/мес (мастер-ТЗ).

---

## СТАРТ

Сначала подтверди, что прочитал пак: перечисли 5 флагманских/критичных фактов (домены, LLM_PCT, front IP, роль HA, статус Метрики).  
Потом выдавай полный OUTPUT FORMAT без вопросов «а точно ли уходить с Cursor?» — решение владельца уже принято.
