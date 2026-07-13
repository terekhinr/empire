# Снегири · мастер-сессии Gemini · промпты для уточнения перед работой

**Дата:** июль 2026  
**Зачем:** мы **прервали** пакетную генерацию 50 мультиков — сначала «как по учебнику»: стратегия, gate'ы, канон, A/B, школы.  
**Порядок:** Сессия 0 → A → … → M. **Не генерировать каталог**, пока не закрыта Сессия 0 + A + H (хотя бы 2 пилота в catalog).

**Связано:** [`snegiri_product_prelaunch_methodology.md`](snegiri_product_prelaunch_methodology.md) · [`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md) · [`snegiri_go_nogo_master.md`](snegiri_go_nogo_master.md) · [`snegiri_comic_errors_catalog.md`](snegiri_comic_errors_catalog.md)

**Как работать:** новый чат Gemini · режим с текстом (картинки — только в K, L, пилотах). Вложения: `hero-poster.png`, при необходимости — скрин неудачной ленты из `assets/comics/`.

**Ответы Cursor (13.07):** [`snegiri_INDEX_for_gemini_audit.md`](snegiri_INDEX_for_gemini_audit.md) · сессии 0, A, B, J в `docs/snegiri_gemini_session_*.md` — **сверь в Gemini параллельно**.

---

## Карта сессий

| # | Тема | Когда | Выход |
|---|------|-------|-------|
| **0** | Мастер-аудит всего пакета | Первым | Приоритетный gate-checklist |
| **A** | Предзапуск продукта (методологии) | До контента | Дополненная методология + GO/NO-GO |
| **B** | Finmodel v4 + unit economics | После A | Таблица сценариев, kill-metrics |
| **C** | Русский язык везде | Параллельно | Глоссарий RU, список переименований |
| **D** | Мерч на моделях и стенах | Перед пилотами | Решение A/B стены + бренд-гайд |
| **E** | Industrial gym vs дом | Перед A/B локации | Формула копирайта + визуала |
| **F** | 1 гиря base / 2 гири advanced | Перед A/B гирь | Продуктовая лестница снаряда |
| **G** | M/F, A/B матрица, QA | Перед генерацией | Протокол приёмки |
| **H** | Ошибки по школам (25 упр.) | По 1 slug за раз | Заполнение errors_catalog |
| **I** | Workflow «одно упражнение» | Операционка | Календарь на 8 недель |
| **J** | Разбор провала 50 лент | После 0 | Negative prompt list |
| **K** | Пилот rack_hold (полный пакет) | После D,E,G | Готовый промпт M+F |
| **L** | Пилот jerk (полный пакет) | После K | Готовый промпт M+F |
| **M** | Финальный gate перед волной 1 | Последним | GO / NO-GO на генерацию |
| **N** | **Синтез Cursor + OpenRouter** | После 0,A,B,J + OpenRouter | Вердикт по спорам, план 14 дней |

---

# СЕССИЯ 0 · Мастер-аудит (начать здесь)

**Вложения:** нет (или 1 скрин `swing_m.webp` с штангой на фоне как антипример).

```
Роль: ты — product strategist + art director + NPD-консультант для цифрового фитнес-продукта «Снегири не гири» (snegirinegiri.ru).

Контекст:
- PWA с программой «спина (McGill) → гиря», CV-разбор видео, подписка ~590 ₽/мес.
- Мы сгенерировали ~50 комикс-эталонов пакетом — качество плохое: штанги в кадре, EN/RU вперемешку, 1 vs 2 гири, мужчина и женщина с разной хореографией.
- Генерацию ОСТАНОВИЛИ. Сначала — «как по учебнику»: методологии предзапуска, канон, A/B, школы тренеров.

Я пришлю тебе структурированный бриф наших решений за сегодня (ниже). Твоя задача — НЕ рисовать, а провести аудит.

БРИФ РЕШЕНИЙ (черновик, проверь и оспорь слабые места):

1. ЯЗЫК: все подписи, ошибки, названия упражнений — русский. Запрет EN (ST, DRIVE, Push press как заголовок).

2. МЕРЧ: чёрная футболка, белый line-art снегирь на гире на груди 8–10 см; шорты/леггинсы без логотипов; стены зала — либо чистый industrial, либо лёгкий трафарет «СНЕГИРИ» (A/B).

3. ЛОКАЦИЯ: продукт = тренировка ДОМА с одной гирей. Визуал эталона = industrial gym (как YouTube Руднев/Денисов), но в фокусе ТОЛЬКО гиря(и) — без штанги, стоек, блинов.

4. СНАРЯД: весь стартовый курс — 1×16 кг (halo 12 кг, резина S4). Две гири — tier advanced (пока farmer_walk_2kb).

5. M/F: сначала мужчина → QA → женщина с референсом M, та же хореография, одноручные — правая рука.

6. ОШИБКИ: не «от балды» — из школ Алферова, Денисов, Руднев, McGill. Пример: толчок — локоть на подвздошную кость, не локти в стороны; ERROR — отжим или отведённые локти.

7. ОБЪЁМ: не 25 сразу — по 1 упражнению: catalog → brief → Gemini → QA. Основной генератор — Gemini, Cursor только A/B.

8. ПРЕДЗАПУСК: Stage-Gate, Lean, JTBD, VPC, Van Westendorp, PMF — см. отдельный doc (пришлю в Сессии A).

ЗАДАНИЕ (структурированный ответ на русском):

A. Согласованность: где в брифе внутренние противоречия? (дом vs зал, доверие vs копирайт, 1 гиря vs «профи в зале»)

B. Риски: топ-10 рисков если запустим генерацию без gate'ов (продукт, юридика McGill, бренд, LTV).

C. Gate-checklist: 15–25 пунктов «можно генерировать пилот» vs «нельзя». Формат: [ ] пункт | критерий PASS | кто проверяет | срок.

D. Приоритет сессий A–M: в каком порядке прогонять промпты ниже и что блокирует что.

E. 3 жёстких рекомендации «остановить херню и делать серьёзно» — конкретно для нашего кейса, не общие слова.

F. Что спросить у основателя (меня) — не больше 5 вопросов, только блокирующие.

Не предлагай «сгенерировать все 25 мультиков». Предлагай минимальный proof path.
```

**После ответа:** сохранить в `docs/snegiri_gemini_session_0_audit.md` (вручную) и обновить чеклист в `go_nogo_master.md`.

---

# СЕССИЯ A · Предзапуск продукта · методологии «как по учебнику»

**Вложение:** текст [`snegiri_product_prelaunch_methodology.md`](snegiri_product_prelaunch_methodology.md) (вставить целиком или §1–12).

```
Роль: консультант по NPD и go-to-market для подписочного health-tech в РФ.

Продукт: «Снегири не гири» — PWA, CV-разбор техники, программа McGill → гиря, 590/1490/3990 ₽, канал Штерн, домен snegirinegiri.ru.

Контекст основателя: ~3+ дня dev уже вложено; есть лендинг, программа v3.1, stub CV; нет 10 платящих beta; эталонные видео тренеров — в переговорах (kill K0).

Ниже — наш черновик карты методологий (Stage-Gate, Lean Startup, JTBD, Value Proposition Canvas, Business Model Canvas, Crossing the Chasm, Van Westendorp, Sean Ellis PMF, TAM/SAM/SOM, RICE, AARRR, Design Thinking, Discovery-Driven Planning, Kano, SWOT). [ВСТАВЬ СЮДА СОДЕРЖИМОЕ ФАЙЛА snegiri_product_prelaunch_methodology.md]

ЗАДАНИЕ:

1. ПРОВЕРКА ПОЛНОТЫ: какие важные методики/стадии мы пропустили для digital subscription fitness в 2024–2026? (например: Regulatory, Privacy, Cohort analysis, CAC payback по каналам, Jobs-based segmentation, Whole Product Moore, и т.д.) — добавь таблицей.

2. АДАПТАЦИЯ STAGE-GATE: перепиши 6–7 gate'ов именно для Снегири с deliverable на каждом и честным статусом «сейчас / не сделано». Укажи, почему генерация 50 мультиков была ошибкой с точки зрения Stage-Gate.

3. LEAN + JTBD: сформулируй 5 проверяемых гипотез на ближайшие 4 недели (формат: «Мы верим, что… Мы измерим… Порог успеха… Pivot если…»).

4. VALUE PROPOSITION CANVAS: заполни полностью для beachhead «офисный гиревик 30–50, страх поясницы». Customer jobs, pains, gains, pain relievers, gain creators — по 4–6 пунктов каждый.

5. KANO для MVP: классифицируй фичи (must / performance / delight): CV разбор, программа, 1 мультик, 25 мультиков, OAuth, LLM-coach, 2 гири advanced, Metrika, ЮKassa.

6. GTM 90 дней: план Acquisition → Activation → Retention без paid до 30 organic paid subs. Каналы: TG Штерн, TG Снегири, Дзен. KPI по неделям.

7. ЧТО НЕ ДЕЛАТЬ: список из 8–12 активностей-ловушек («херня вместо серьёзного дела») — типичных для соло-основателя в нашем кейсе.

8. ИТОГ: один артефакт «Pre-launch playbook Снегири v1» — оглавление из 12 разделов с 2–3 предложениями на раздел, готовое для Notion/doc.

Язык: русский. Цифры — осторожные, с диапазонами. Ссылайся на методологии по имени (Cooper, Ries, Christensen, Osterwalder, Moore, Van Westendorp, Ellis).
```

---

# СЕССИЯ B · Finmodel v4 · честные сценарии

**Вложение:** [`snegiri_finmodel_v3.md`](snegiri_finmodel_v3.md) или v4 если есть.

```
Роль: CFO-аналитик subscription SaaS / edtech в РФ.

Продукт: Снегири — ARPU 590 ₽ (base), churn гипотеза 6–15%/мес, COGS разбор ~12–25 ₽, CAC organic + время основателя, RevShare тренерам 20–25% опционально.

Kill-metrics из go_nogo:
- K0: нет договора съёмки с тренером к дате → стоп
- Нужно ≥10 платящих beta OR лицензия эталонов
- LTV/CAC > 1 в base case

[ВСТАВЬ КЛЮЧЕВЫЕ ЦИФРЫ ИЗ finmodel v3/v4]

ЗАДАНИЕ:

1. Построй 3 сценария на 12 месяцев: pessimistic / base / optimistic — таблица MRR, subs, churn, marketing spend, founder hours cost.

2. Посчитай: LTV, CAC, LTV/CAC, payback months, break-even subs для каждого сценария. Формулы явно.

3. Sensitivity: что если churn 15% vs 6%? что если конверсия free→paid 1% vs 5%? что если только 1 мультик вместо 25 — влияние на retention (качественно + количественно если можешь).

4. Opportunity cost: 5 недель на 25 мультиков vs 5 недель на custdev + 10 beta pay — что рациональнее для GO/NO-GO?

5. Рекомендация: минимальный бюджет контента (₽ и часы) до первого платящего vs «каталог мультиков».

6. 5 красных флагов в старых оптимистичных моделях — что мы недооценивали.

Вывод: «Finmodel v4 recommendations» — bullet list с конкретными переменными для таблицы Google Sheets.
```

---

# СЕССИЯ C · Русский язык · глоссарий и UX

```
Роль: UX writer + редактор фитнес-контента для русскоязычной аудитории 30–50 лет.

Продукт: приложение с комикс-эталонами, фазами упражнений, CV-ошибками. Сейчас в коде смешение: Push press, Bird-dog, Jerk, ERROR bell…, ST/DRIVE.

Список 25 slug (латиница): curl_up, side_plank, bird_dog, pallof_press, hip_hinge, goblet_squat, suitcase_carry, farmer_walk, swing, one_arm_swing, hand_switch, halo, rack_hold, clean, press, push_press, high_pull, snatch, jerk, tgu_partial, tgu_full, windmill, bent_press, bottoms_up, (проверь полный список program_data).

ЗАДАНИЕ:

1. Таблица: slug | name_ru (канон) | name_ru_short для подписи на ленте | school_term если отличается | «не использовать»

2. Стиль подписей на комиксе: CAPS или sentence case? длина max символов? формат ERROR: «ОШИБКА: ЛОКТИ» vs «Ошибка: локти» — выбери один стандарт и обоснуй.

3. Глоссарий 30 терминов: подрыв, мёртвая точка, стойка, фиксация, треугольник локтей, подвздошная кость (как писать для новичка без мед. жаргона).

4. Локализация app vs лендинг vs мультик — одна терминология или допустимы синонимы?

5. SEO: какие RU-фразы в meta/description не дублируя brand «Снегири».

6. Чеклист QA «нет английского на картинке» — 10 пунктов для художника/ИИ.

Не переводи бренд «Снегири не гири». McGill можно как «по Макгиллу».
```

---

# СЕССИЯ D · Мерч · одежда · стены зала

**Вложения:** `hero-poster.png`, опционально скрин TG-канала.

```
Роль: brand designer + merchandise strategist для брутального фитнес-бренда (ч/б + #FF3300).

Бренд: «Снегири не гири», знак — снегирь на гире (line-art), тон Штерна — суровый, не wellness-pastel.

Контекст мультиков: атлеты M/F в industrial gym, CV-скелет поверх, эталон техники.

Варианты:
- Футболка: белый снегирь на гире на груди 8–10 см
- Шорты/леггинсы: чёрные без принта
- Стены: A) чистый бетон/металл B) тонкий трафарет «СНЕГИРИ» или силуэт в углу C) портрет Штерна — отложить

ЗАДАНИЕ:

1. Brand book lite (1 страница): что на модели, что на стенах, что запрещено (Nike, SF, чужие клубы, мотивационные постеры).

2. A/B тест стены A vs B: гипотеза, метрика (доверие, отвлечение от техники, узнаваемость бренда), рекомендация default для MVP.

3. Нужен ли мерч на шортах (мелкий принт сбоку) или отвлекает от CV? Аргументы.

4. Промпт-блок на английском (для image gen) — 8–12 строк, copy-paste в каждый brief: одежда, лого на груди, стены, запреты.

5. Отличие мерча на лендинге vs мультике vs будущем видео с тренером (реальная одежда) — как не разъехаться.

6. 5 типичных ошибок ИИ-генерации мерча (логотип Nike, огромный принт, цветная гиря) — negative prompts.

Ответ: RU + EN prompt block в конце.
```

---

# СЕССИЯ E · Industrial gym vs дом · продуктовый анализ

```
Роль: product marketer + визуальный стратег.

Дилемма:
- Копирайт продукта: «одна гиря дома», без абонемента в зал.
- Запрос на визуал: профессионалы на фоне industrial gym (как Руднев/Денисов на YouTube).
- Провал пакетной генерации: industrial gym → штанги и стойки в кадре.

Рабочая формула (проверь):
«Тренируешься дома с одной гирей. Эталон снят в стиле industrial gym — как у тренеров, но в кадре только твой снаряд.»

ЗАДАНИЕ:

1. Разложи на 4 слоя: (а) обещание лендинга (б) программа в app (в) комикс-эталон (г) съёмка пользователя дома — что должно совпадать, что может отличаться.

2. Психология доверия для ЦА 30–50: домашний коврик vs industrial gym — что сильнее для конверсии в 590 ₽? Ссылки на паттерны (не выдумывай исследования — помечай «гипотеза»).

3. A/B локации: industrial_gym vs home_room на swing и curl_up — что измеряем, какой размер выборки «на глаз» достаточен для визуального решения (не статистика).

4. Текст для app под эталоном: 2–3 варианта hint «сними дома с тем же ракурсом».

5. Риски юридического/этического: пользователь не может воспроизвести industrial gym дома — как не создать ощущение обмана.

6. Рекомендация: default location в brief + условия когда home_room лучше (S-трек McGill?).

7. Промпт-формулировка LOCATION для image gen (EN, 6 строк) — жёсткий запрет штанги при gym-эстетике.

Итог: одна зафиксированная «формула зал+дом» для strategy_v2.md.
```

---

# СЕССИЯ F · Снаряд · 1 гиря base vs 2 гири advanced

```
Роль: program director гиревой школы + product manager.

Правило: весь стартовый курс — 1×16 кг (исключения: halo 12 кг, резина S4, bodyweight McGill).
Продвинутый tier: farmer_walk с 2×16 кг — отдельные файлы farmer_walk_2kb_*.

Проблема пакетной генерации: на одном кадре 2 гири, на другом 1; женщина «одной гирей в две стороны».

ЗАДАНИЕ:

1. Продуктовая лестница снаряда: неделя 1 → неделя 12 → advanced — когда впервые упоминать вторую гирю? когда показывать эталон 2 гирь в UI?

2. Таблица всех 25 упражнений: slug | base equipment | advanced variant? | grip | working hand

3. A/B пилот: farmer_walk tier base (1 гиря правая) vs tier advanced (2 гири) vs suitcase_carry (1 гиря) — как визуально не перепутать? критерии QA.

4. Копирайт: «не нужно покупать вторую гирю» на старте — где сказать на лендинге/onboarding.

5. Промпт-строки для image gen: TIER BASE — EXACTLY ONE kettlebell / TIER ADVANCED — TWO identical 16kg — формулировки без двусмысленности.

6. Ошибки ИИ: «две гири на свинге», «гиря в левой и правой на одноручном» — negative list + reference rule для F от M.

7. Нужны ли ещё упражнения с advanced 2kb кроме farmer? (двуручный farmer, double clean — или нет на MVP)

Итог: решение зафиксировать в comic_spec + ab_tests §2.
```

---

# СЕССИЯ G · M/F · A/B · QA · Gemini vs Cursor

```
Роль: QA lead + экспериментальный дизайнер для визуального контента.

Пайплайн:
1. M → QA → F с референсом M (та же хореография, та же гиря, правая рука)
2. A/B: industrial_gym vs home_room (4 img)
3. A/B: farmer 1 vs 2 гири (2–4 img)
4. A/B: clean M→F strip vs panel-by-panel (4 img)
5. A/B: стена чистая vs мерч (2 img)
6. A/B: Gemini vs Cursor same prompt (2 img)

ЗАДАНИЕ:

1. Матрица экспериментов: приоритет, зависимости (что сначала), минимальный набор картинок до волны 1.

2. Протокол приёмки одной ленты — 20 пунктов чеклиста (RU, гири, локти, фон, мерч, ERROR, watermark, M=F).

3. M→F: когда strip reference лучше, когда покадровая склейка? критерии для clean.

4. Gemini primary, Cursor A/B — правила: кто source of truth, как логировать расхождения.

5. Шаблон журнала A/B (таблица: дата, тест, варианты, победитель, скрин, комментарий).

6. Definition of Done для status: ok в comic_briefs.json.

7. Оценка лимита Gemini ~2 img/день — реалистичный календарь на 8 пилотных упражнений.

Не предлагай генерировать 50 лент.
```

---

# СЕССИЯ H · Ошибки по школам · методология + очередь 25

**Запускать по одному slug.** Ниже — мастер-промпт; в конце подставляй `{SLUG}`.

```
Роль: методист гиревого спорта + консультант по биомеханике. Школы: Алферова (стойка, толчок), Денисов (заброс, жим), Руднев (свинг, рывок), McGill (спина), StrongFirst RU, ФГОС Горбунов.

Задача: заполнить каталог ошибок для ОДНОГО упражнения — для комикс-эталона и будущего видео CV.

Упражнение: {SLUG}
Камера из program: {CAMERA}
База: 1 гиря 16 кг если K-трек (уточни по slug).

ЗАДАНИЕ для {SLUG}:

1. name_ru каноническое.

2. school_primary + 1–2 secondary.

3. panels_correct: 3–6 фаз — label RU (CAPS) | cue что делает атлет | school_note (кто так учит).

4. error_panel: одна самая частая ошибка новичка-дома:
   - label: «ОШИБКА: …»
   - mistake: описание
   - red_line_zone: анатомия
   - school_source
   - common_in

5. «НЕ РИСОВАТЬ»: 3–5 антипаттернов (как у нас было: локти в стороны на толчке, штанга, две гири на одноручном).

6. references_youtube: 2–4 канала/темы (без выдуманных таймкодов — «тема: стойка толчок»).

7. EN блок для image prompt (technique): 5–8 строк для вставки в render_comic_prompt (локоть на iliac crest и т.д.).

8. Сверка с соревновательной техникой vs «фитнес-стойка» — где новичок путает.

Формат ответа: YAML как в шаблоне errors_catalog.md.

После ответа я вставлю в docs/snegiri_comic_errors_catalog.md и пересоберу brief.
```

**Очередь slug для H (25 сообщений):**

| # | slug | school anchor |
|---|------|---------------|
| 1 | rack_hold | Алферова |
| 2 | jerk | Алферова |
| 3 | clean | Денисов |
| 4 | swing | Руднев |
| 5 | curl_up | McGill |
| 6 | side_plank | McGill |
| 7 | bird_dog | McGill |
| 8 | snatch | Руднев |
| 9 | press | Денисов/SF |
| 10 | hand_switch | Руднев/ФГОС |
| 11–25 | остальные по program_data | … |

---

# СЕССИЯ I · Workflow «одно упражнение» · календарь

```
Роль: operations manager контент-студии.

Ограничения: Gemini ~2 изображения/день; основатель параллельно DNS, тренеры, сайт; Cursor только A/B.

Пайплайн:
errors_catalog[slug] → build_comic_briefs.py → render_comic_prompt.py → Gemini M → QA → Gemini F + ref M → slice → status ok

ЗАДАНИЕ:

1. Календарь на 8 недель: неделя | slug | A/B если нужен | deliverable | gate

2. Роли: основатель vs Gemini vs Cursor vs скрипты — кто что делает.

3. WIP limit: сколько slug одновременно (ответ: 1).

4. Артефакты в репо после каждого slug (файлы, status в json).

5. Escalation: когда остановить волну (3 провала QA подряд).

6. Параллельный трек: переговоры с тренерами (K0) — не блокирует ли мультики или блокирует?

7. Шаблон qa_notes для comic_briefs.json.

Итог: Gantt текстом + «неделя 0 = только A/B пилоты, не каталог».
```

---

# СЕССИЯ J · Разбор провала · 50 лент · negative prompts

**Вложения:** 3–5 худших примеров (`swing_m.webp`, `jerk_m.webp`, …).

```
Роль: forensics для ИИ-генерации фитнес-контента.

Мы сгенерировали ~50 горизонтальных комикс-лент (25 slug × M/F) пакетом без единого brief. Типичные дефекты:
- штанга, стойки, блины в кадре
- подписи EN и RU вперемешку (ST, DRIVE, ERROR bell)
- 1 vs 2 гири непоследовательно
- M правильная стойка, F — «одна гиря в две стороны»
- толчок: локти в стороны вместо локоть на подвздошную (Алферова)
- industrial gym промпт без FORBIDDEN

ЗАДАНИЕ:

1. Классификация дефектов: категория | частота | корневая причина | fix в процессе

2. TOP-15 negative prompts (EN) для image generation — copy-paste block.

3. TOP-10 positive mandatory lines (EN) — что должно быть в КАЖДОМ промпте.

4. Почему пакетная генерация F без M обречена — технически и процессно.

5. Можно ли спасти что-то из 50 или только _draft/архив? критерии.

6. Сообщение для основателя: «что мы выбросили и почему это правильно» — 1 абзац жёстко но по делу.

Не предлагай перегенерировать все 50. Предложи минимальный пилот 2 упражнения.
```

---

# СЕССИЯ K · Пилот rack_hold · полный пакет для Gemini

**Вложения:** `hero-poster.png` · текст K5 из errors_catalog · вывод `render_comic_prompt.py --slug rack_hold --performer m`

**Шаг 1 — отправить мастер-промпт сессии (картинки):**

```
Ты — арт-директор snegirinegiri.ru («Снегири не гири»).

ПРОДУКТ: пользователь тренируется ДОМА с одной гирей 16 кг. Эталон — industrial gym эстетика, но в кадре ТОЛЬКО одна гиря. Без штанги, стоек, блинов, чужих логотипов.

ПАЛИТРА: #000000 фон · #FFFFFF тело/гиря/CV-скелет · #FF3300 ТОЛЬКО одна линия на панели ОШИБКА.

МЕРЧ: чёрная футболка, белый line-art снегирь на гире на груди 8–10 см; чёрные шорты/леггинсы без логотипов.

ЯЗЫК: все подписи на изображении — РУССКИЙ КИРИЛЛИЦА, IBM Plex Mono стиль, CAPS. Без английского.

ТЕХНИКА (Алферова, стойка): гиря на груди; локти прижаты к корпусу; треугольник локти–запястья–гира; НЕ «локти-крылья» 90° в стороны.

ПОРЯДОК: сначала M. После моего QA — F с референсом M (та же хореография).

Сгенерируй изображение только когда я пришлю полный brief упражнения. Сейчас подтверди, что правила понятны, и перечисли 5 типичных ошибок, которых ты избежишь на rack_hold.
```

**Шаг 2 — brief M (вставить output скрипта + technique block):**

```bash
python3 scripts/render_comic_prompt.py --slug rack_hold --performer m
```

Дописать вручную в конец промпта:

```
TECHNIQUE BLOCK (mandatory):
- Rack position: kettlebell on forearms at chest, wrists neutral.
- Elbows pinned to ribs/torso — compact triangle from front 45° view.
- ERROR panel: elbows flared sideways, kettlebell drifting forward — red #FF3300 line on flared elbow only.
- EXACTLY ONE 16kg kettlebell. RIGHT hand N/A (two-hand rack).
- NO elbows 90° abducted like crossfit front rack.
```

**Шаг 3 — после QA M, F:**

```bash
python3 scripts/render_comic_prompt.py --slug rack_hold --performer f
```

+ приложить утверждённый `rack_hold_m.png` и строку: `REFERENCE: duplicate choreography from attached M strip, only change athlete to woman 35, black leggings.`

---

# СЕССИЯ L · Пилот jerk · полный пакет (толчок)

Аналогично K. Критичный technique block:

```
TECHNIQUE BLOCK — JERK (Alferova / competition rack):
- Rack: elbow tucked against hip/iliac crest, forearm vertical on torso — NOT elbows flared 90° to sides.
- Dip: shallow knee bend, rack preserved.
- Drive: impulse from legs, bell floats — NOT early press with arms.
- Fixation: arms straight overhead, pause.
- ERROR panel: «ОШИБКА: ОТЖИМ» — re-bending elbows to press bell after fixation; red line on bending elbow.
- Alternative ERROR for later pass: «ОШИБКА: ЛОКТИ» — elbows flared in rack.
- EXACTLY ONE 16kg kettlebell in RIGHT hand only for one-arm jerk if brief says one-arm; if two-hand jerk in program — BOTH hands, still ONE bell.
```

```bash
python3 scripts/render_comic_prompt.py --slug jerk --performer m
python3 scripts/render_comic_prompt.py --slug jerk --performer f  # после QA M
```

---

# СЕССИЯ M · Финальный gate · GO на волну 1

```
Роль: инвестор-скептик + product lead.

Контекст: пройдены сессии 0–L (частично). Нужно решение: начинаем волну 1 мультиков или ещё рано.

Входные данные (заполню я):
- [ ] Сессия 0 audit: топ-риски
- [ ] A/B локация: победитель =
- [ ] A/B стена: победитель =
- [ ] A/B farmer 1 vs 2: решение =
- [ ] rack_hold M+F: QA pass? да/нет
- [ ] jerk M+F: QA pass? да/нет
- [ ] K0 тренер: статус переговоров
- [ ] Beta pay: N платящих =
- [ ] Finmodel v4: LTV/CAC base =

ЗАДАНИЕ:

1. GO / NO-GO / GO WITH CONDITIONS — однозначно.

2. Если GO: точный scope волны 1 (какие slug, не больше N).

3. Если NO-GO: что сделать за 7 дней до повторного gate.

4. Kill-metrics на 30 дней после старта волны.

5. Одна фраза для основателя: «серьёзное дело началось» vs «мы снова делаем херню» — честная оценка текущего состояния.

Без утешений. Русский язык.
```

---

# СЕССИЯ N · Синтез Cursor + OpenRouter (третье мнение)

**Когда:** после прогона OpenRouter и черновиков Cursor 0/A/B/J.  
**Режим:** только текст.  
**Готовый промпт (copy-paste):** [`snegiri_gemini_session_N_synthesis_prompt.md`](snegiri_gemini_session_N_synthesis_prompt.md)

Кратко: Gemini выступает **арбитром** между Cursor и DeepSeek по спорам (дом vs industrial gym, юридика, годовой тариф, первый пилот), даёт GO/NO-GO, gate v2, план 14 дней, negative prompts.

**Ответ сохранить в:** `docs/snegiri_gemini_session_N_synthesis.md`

---

## Быстрые команды (локально)

```bash
# Мастер-промпт для картинок (короткий)
python3 scripts/render_comic_prompt.py --master

# Пилоты
python3 scripts/render_comic_prompt.py --slug rack_hold --performer m
python3 scripts/render_comic_prompt.py --slug jerk --performer m
python3 scripts/render_comic_prompt.py --slug swing --performer m --ab-location home_room
python3 scripts/render_comic_prompt.py --slug swing --performer m --ab-location industrial_gym
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier base
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier advanced
```

---

## Порядок на эту неделю (рекомендация)

| День | Сессия | Действие |
|------|--------|----------|
| 1 | **0** + **A** | Аудит + методология в Gemini → сохранить ответы |
| 2 | **E** + **D** | Формула зал/дом + мерч → зафиксировать A/B стены |
| 3 | **F** + **G** | Гири + матрица A/B → 6–10 пилот-картинок в Gemini |
| 4 | **H** ×2 | rack_hold + jerk в catalog (если не готовы) |
| 5 | **K** | Первый эталон M+F rack_hold |
| 6 | **L** | jerk M+F |
| 7 | **M** | Gate на волну 1 |

*«Как по учебнику» = сначала документы и gate, потом ассеты.*
