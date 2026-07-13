# OpenRouter · прогон Снегири · итоги и что дальше

**Дата:** 2026-07-13  
**Скрипт:** `scripts/run_snegiri_openrouter_sessions.py`  
**Мета (токены, $):** [`snegiri_openrouter_sessions_meta.json`](snegiri_openrouter_sessions_meta.json)

---

## 1. Что сделано

| Сессия | Файл ответа | Модель | Стоимость USD |
|--------|-------------|--------|---------------|
| **0** Аудит | [`snegiri_openrouter_session_0_audit.md`](snegiri_openrouter_session_0_audit.md) | deepseek/deepseek-chat | **$0.0015** |
| **A** Предзапуск | [`snegiri_openrouter_session_A_prelaunch.md`](snegiri_openrouter_session_A_prelaunch.md) | deepseek/deepseek-chat | **$0.0033** |
| **B** Finmodel | [`snegiri_openrouter_session_B_finmodel.md`](snegiri_openrouter_session_B_finmodel.md) | deepseek/deepseek-chat | **$0.0022** |
| **J** Провал 50 лент | [`snegiri_openrouter_session_J_comic_failure.md`](snegiri_openrouter_session_J_comic_failure.md) | deepseek/deepseek-chat | **$0.0009** |

**Итого за прогон 0+A+B+J:** ~**$0.008** (меньше 1 ₽).  
**Время:** ~3 минуты.

---

## 2. Какие модели пробовали

### ❌ Не работают с этого VPS (OpenRouter)

| Модель | Ошибка | Почему |
|--------|--------|--------|
| `google/gemini-*` | **403** ToS | Google блокирует запросы с этого региона/сервера |
| `openai/gpt-4o-mini` | **403** ToS | То же |
| `anthropic/claude-*` | 404 / 403 | Нет эндпоинта или ToS |

**Вывод:** Gemini через OpenRouter API с VPS **не вариант** (как и прямой Gemini API с 429). Картинки — **gemini.google.com в браузере**.

### ✅ Работают (дешёво)

| Модель | Роль | Ориентир цены |
|--------|------|----------------|
| **`deepseek/deepseek-chat`** | **Основная** для аудитов RU | ~$0.14 / 1M входных токенов |
| `qwen/qwen-2.5-72b-instruct` | Запасная, длинные отчёты | чуть дороже, сильнее |
| `qwen/qwen-2.5-7b-instruct` | Самая дешёвая | для черновиков |
| `mistralai/mistral-small-3.1-24b-instruct` | Запасная EU | средняя цена |

Повторный прогон:
```bash
cd /root/projects/empire
./venv/bin/python scripts/run_snegiri_openrouter_sessions.py
./venv/bin/python scripts/run_snegiri_openrouter_sessions.py --session B
```

---

## 3. Сводка ответов (простым языком)

### Сессия 0 · Аудит

**Согласен с нами:**
- Пакет 50 лент без gate'ов — ошибка
- Одно упражнение за раз
- RU, M→F, школы — must

**Оспорил / ужесточил:**
- Сильнее давит на **юридику McGill** и школ (нужны согласования, не только «цитируем YouTube»)
- Предлагает «**фокус на доме, не зале**» — **расходится** с нашей формулой «дом в продукте / industrial gym на картинке». **Оставляем формулу v2**, но в лендинге явно пишем: «эталон снят как у тренеров, тренируешься дома».

**Gate:** 15 пунктов; минимальный путь = юридика → канон → 1 упражнение → Van Westendorp → пилот.

### Сессия A · Предзапуск

**Добавила полезное:**
- **152-ФЗ / видео на сервере** — политика и TTL (у нас в v3 §L частично)
- **Cohort analysis** — retention по неделям входа
- **CJM** — карта пути пользователя
- Подтвердила: **50 мультиков = прыжок в Gate 5 без Gate 4**

**5 гипотез на 4 недели** — конверсия ≥3%, retention M2 ≥85%, CTR Stern ≥5%.

**12 ловушек** — совпадают с нашим списком (реклама, 25 мультиков, OAuth, LLM…).

### Сессия B · Finmodel

**Согласна с v4:**
- Churn планировать **10%**, не 4%
- Год **3990 ₽** — плохо → **5990** или убрать
- Реклама 80k — NO до GO
- Сначала **10 paying beta**, потом контент

**Цифры DeepSeek (проверь в Sheets):**
- Base LTV ~4590 ₽ @ churn 10% (упрощённая формула без margin)
- LTV/CAC base **1.91** только если CAC низкий; при organic + время основателя CAC высокий

**Красные флаги:** COGS при пике ×2–3, конверсия 1–3% реальна при 114 TG.

### Сессия J · Мультики

См. файл — negative prompts, не спасать 50 лент.

---

## 4. Cursor vs OpenRouter vs Gemini web

| Источник | Файлы | Когда использовать |
|----------|-------|-------------------|
| **Cursor** | `snegiri_gemini_session_0/ A/ B/ J_*.md` | Уже в репо, детальные gate и цифры |
| **OpenRouter** | `snegiri_openrouter_session_*.md` | Второе мнение за копейки |
| **Gemini web** | Ты вручную | Картинки + оспорить оба текста |

**Расхождение №1:** OpenRouter 0 говорит «только дом»; мы — **industrial gym на эталоне**. Решение: не менять без A/B (4 картинки).

**Расхождение №2:** OpenRouter сильнее про юридику школ — **принять:** в outreach/LICENSE явно «методика вдохновлена», не «сертификат McGill».

---

## 5. Что делать дальше (последовательно)

### Неделя 1 · Решения (ты)

| # | Действие | Срок |
|---|----------|------|
| 1 | **Годовой тариф:** 5990 / лимит 4 разбора / убрать с лендинга | 1 день |
| 2 | Прочитать OpenRouter 0+A+B; отметить согласен/нет в комментарии | 1 день |
| 3 | **3 ответа на блокирующие вопросы:** стена A/B, rack vs jerk, K0 дедлайн | 1 день |

### Неделя 1 · Продукт (я / ты)

| # | Действие | Срок |
|---|----------|------|
| 4 | Metrika цели — `docs/metrika_goals_setup.md` | 1 час |
| 5 | ЮKassa тестовая оплата | 2–3 дня |
| 6 | A/B локация **4 картинки** — **gemini.google.com** + `render_comic_prompt.py` | 2 дня |

### Неделя 2 · Пилот

| # | Действие |
|---|----------|
| 7 | `rack_hold` M → QA → F (Gemini web) |
| 8 | 5 custdev интервью |
| 9 | 2 поста Stern → бесплатный разбор |

### Неделя 3–4 · Validation

| # | Критерий |
|---|----------|
| 10 | ≥3 платящих beta |
| 11 | Trial→paid на 200+ визитах |
| 12 | Сессия **M** (GO волна 1) — после п.7–10 |

### Не делать до Gate 4

- 25 мультиков  
- Paid реклама 80k  
- Съёмка тренера 45k без K0  
- Gemini/Google API с VPS  

---

## 6. Карта всех файлов аудита

| Тип | Путь |
|-----|------|
| **Индекс** | [`snegiri_INDEX_for_gemini_audit.md`](snegiri_INDEX_for_gemini_audit.md) |
| **Итог прогона** | этот файл |
| Cursor 0/A/B/J | `docs/snegiri_gemini_session_*.md` |
| OpenRouter 0/A/B/J | `docs/snegiri_openrouter_session_*.md` |
| Мета OpenRouter | `docs/snegiri_openrouter_sessions_meta.json` |
| Стратегия мультиков | `docs/snegiri_comic_strategy_v2.md` |
| Finmodel | `docs/snegiri_finmodel_v4.md` |
| GO/NO-GO | `docs/snegiri_go_nogo_master.md` |
| Промпты для Gemini web | `docs/snegiri_gemini_master_sessions.md` |
| Скрипт OpenRouter | `scripts/run_snegiri_openrouter_sessions.py` |

---

*Прогон выполнен автоматически. Сверь с ответом Gemini web и напиши расхождения — внесу в go_nogo.*
