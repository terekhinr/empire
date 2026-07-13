# Снегири · карта файлов · для параллельного аудита в Gemini

**Дата:** 2026-07-13  
**Зачем:** ты проводишь аудит в [gemini.google.com](https://gemini.google.com), я уже заполнил черновики ответов (Cursor). Сверь, оспорь, дополни.

---

## 1. С чего начать в Gemini (порядок)

| Шаг | Файл отдать Gemini | Промпт взять из |
|-----|-------------------|-----------------|
| 1 | [`snegiri_gemini_session_0_audit.md`](snegiri_gemini_session_0_audit.md) | «Проверь аудит, оспорь слабые места, дополни gate-checklist» |
| **1b** | **[`snegiri_gemini_session_N_synthesis_prompt.md`](snegiri_gemini_session_N_synthesis_prompt.md)** | **Синтез Cursor + OpenRouter — арбитраж и план 14 дней** |
| 2 | [`snegiri_gemini_session_A_prelaunch.md`](snegiri_gemini_session_A_prelaunch.md) + [`snegiri_product_prelaunch_methodology.md`](snegiri_product_prelaunch_methodology.md) | Сессия A в [`snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md) |
| 3 | [`snegiri_gemini_session_B_finmodel.md`](snegiri_gemini_session_B_finmodel.md) + [`snegiri_finmodel_v4.md`](snegiri_finmodel_v4.md) | Сессия B в master-sessions |
| 4 | [`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md) | Сессии D, E, F, G |
| 5 | Картинки: `static/snegiri/assets/hero-poster.png` + промпт из терминала | Сессии K, L в master-sessions |

**Мастер-промпты (все сессии):** [`docs/snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md)

---

## 2. Ответы Cursor (уже в репо) — сверить с Gemini

| Файл | Содержание |
|------|------------|
| [`snegiri_gemini_session_0_audit.md`](snegiri_gemini_session_0_audit.md) | Gate-checklist, риски, 5 вопросов основателю |
| [`snegiri_gemini_session_A_prelaunch.md`](snegiri_gemini_session_A_prelaunch.md) | Playbook v1, JTBD, Kano, GTM 90д |
| [`snegiri_gemini_session_B_finmodel.md`](snegiri_gemini_session_B_finmodel.md) | Пересчёт LTV, сценарии, kill-metrics |
| [`snegiri_gemini_session_J_comic_failure.md`](snegiri_gemini_session_J_comic_failure.md) | Negative prompts, почему 50 лент в мусор |
| [`snegiri_self_audit_2026-07-13.md`](snegiri_self_audit_2026-07-13.md) | Самопроверка подготовки |

---

## 3. Стратегия и GO/NO-GO

| Файл | Роль |
|------|------|
| [`snegiri_go_nogo_master.md`](snegiri_go_nogo_master.md) | GO/NO-GO 01.11, kill-metrics, что не делать |
| [`snegiri_product_prelaunch_methodology.md`](snegiri_product_prelaunch_methodology.md) | Stage-Gate, Lean, JTBD, чеклист фаз A–D |
| [`snegiri_finmodel_v4.md`](snegiri_finmodel_v4.md) | **Канон экономики** (P&L, unit economics) |
| [`snegiri_finmodel_v3.md`](snegiri_finmodel_v3.md) | PIVOT, CV-риски §J, тех-чеклист §L |
| [`snegiri_auditoriya_trafik_realist.md`](snegiri_auditoriya_trafik_realist.md) | 114 TG, реалистичная воронка |
| [`snegiri_issledovanie_nulevaya_tochka.md`](snegiri_issledovanie_nulevaya_tochka.md) | Исследование с нуля |

---

## 4. Мультики · канон (не генерить каталог до gate)

| Файл | Роль |
|------|------|
| [`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md) | **Главный канон:** RU, мерч, зал+дом, школы, Gemini workflow |
| [`snegiri_comic_errors_catalog.md`](snegiri_comic_errors_catalog.md) | Техника и ERROR по школам (5/25 готово) |
| [`snegiri_comic_ab_tests.md`](snegiri_comic_ab_tests.md) | Протокол A/B локация, гири, M/F |
| [`snegiri_comic_ab_prompts.md`](snegiri_comic_ab_prompts.md) | Команды для пилотов |
| [`snegiri_comic_gemini_workflow.md`](snegiri_comic_gemini_workflow.md) | Одно упражнение за цикл |
| [`snegiri_comic_prompts.md`](snegiri_comic_prompts.md) | Справочник + ссылки (старые § устарели) |
| [`snegiri_comic_spec_v1.md`](snegiri_comic_spec_v1.md) | История (superseded → v2) |

### Данные и скрипты

| Путь | Роль |
|------|------|
| `snegiri_kb/comic_briefs_data.json` | Канон 25 упражнений (`needs_regen`) |
| `snegiri_kb/comic_phases_data.json` | Фазы RU для плеера |
| `scripts/render_comic_prompt.py` | Промпт для Gemini web / картинок |
| `scripts/build_comic_briefs.py` | Пересборка brief |
| `scripts/gemini_session.py` | Текстовые сессии через API (квота 429 — не работает) |
| `static/snegiri/assets/comics/` | 50 WebP — **не финал**, перегенерация |
| `static/snegiri/assets/hero-poster.png` | Референс стиля для Gemini |

**Промпт одного упражнения:**
```bash
cd /root/projects/empire
./venv/bin/python scripts/render_comic_prompt.py --slug rack_hold --performer m
```

---

## 5. Продукт и лендинг

| Путь | Роль |
|------|------|
| `static/snegiri/index.html` | Лендинг |
| `static/snegiri/` | PWA, js, assets |
| `snegiri_kb/program_data.py` | Программа 25 упражнений |
| [`snegiri_trainers_outreach.md`](snegiri_trainers_outreach.md) | Письма тренерам (K0) |
| [`stern_kettlebell_ai_trainer_tz.md`](stern_kettlebell_ai_trainer_tz.md) | ТЗ продукта |

---

## 6. Что сделать тебе в Gemini web

### Текст (без картинок)

1. Новый чат → вставь **Сессию 0** из [`snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md)  
   Или: «Сверь и улучши» + приложи `snegiri_gemini_session_0_audit.md`

2. То же для **A** и **B** — сравни с моими `session_A`, `session_B`

3. Ответы с расхождениями — **вставь сюда в Cursor** → обновлю doc

### Картинки (когда дойдёшь до пилотов)

1. Прикрепи `hero-poster.png`  
2. Вставь stdout:
   ```bash
   ./venv/bin/python scripts/render_comic_prompt.py --master
   ./venv/bin/python scripts/render_comic_prompt.py --slug rack_hold --performer m
   ```
3. + блок technique из `snegiri_comic_errors_catalog.md` (K5 rack_hold)

---

## 7. Блокирующие решения (ответь когда готов)

1. Годовой тариф: **5990 / лимит / убрать**  
2. Стена зала: **чистая / трафарет**  
3. Старт пилота: **rack_hold / jerk**  

---

## 8. API Gemini

Ключ в `.env` — **429 quota**. Для Снегири используй **gemini.google.com** (аккаунт), не API. Текстовые черновики уже в `docs/snegiri_gemini_session_*.md`.

---

*Корень проекта: `/root/projects/empire` · индекс: этот файл.*
