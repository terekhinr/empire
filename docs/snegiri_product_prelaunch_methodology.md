# Снегири · предзапуск продукта · методологии «как по учебнику»

**Дата:** июль 2026  
**Цель:** не «допилить фичи», а пройти **стадии оценки продукта до рынка**, как в маркетинге и NPD-литературе.  
**Связано:** [`snegiri_go_nogo_master.md`](snegiri_go_nogo_master.md) · [`snegiri_issledovanie_nulevaya_tochka.md`](snegiri_issledovanie_nulevaya_tochka.md) · [`snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md)

---

## 0. Принцип

> Серьёзное дело начинают не с генерации 50 картинок, а с **доказательств**: кому продаём, за что платят, что минимально нужно, когда STOP.

У нас уже есть: лендинг, PWA, программа v3.1, GO/NO-GO рамка. **Не хватает:** формального прохождения gate'ов и единого пакета артефактов до масштабной разработки контента (мультики, CV, видео).

---

## 1. Карта методологий (что используют в индустрии)

| Методология | Автор / источник | Зачем | Что даёт на выходе |
|-------------|------------------|-------|-------------------|
| **Stage-Gate** | Cooper, Kleinschmidt | NPD без «туннеля» — funnel с Go/Kill | Gates, критерии, business case |
| **Discovery-to-Launch** | Stage-Gate International | Полный pipeline discovery → launch → post-launch | 6 критериев gate: стратегия, продукт, рынок, техника, синергии, финансы |
| **Lean Startup** | Eric Ries | Гипотезы → MVP → измерение → pivot | Build-Measure-Learn, MVP, pivot/persevere |
| **Jobs To Be Done (JTBD)** | Christensen; Ulwick | Покупают не фичу, а «работу» | Job story, outcomes, сегменты |
| **Value Proposition Canvas** | Osterwalder (Strategyzer) | Стык боли клиента и обещания продукта | Customer profile + value map |
| **Business Model Canvas** | Osterwalder | Бизнес целиком на одной странице | 9 блоков, unit economics |
| **Crossing the Chasm** | Geoffrey Moore | От early adopters к массовому рынку | Beachhead, whole product |
| **Van Westendorp (PSM)** | Van Westendorp | Цена «слишком дёшево / дорого» | Оптимальная зона цены |
| **Sean Ellis PMF** | «How disappointed…» | Product-Market Fit | ≥40% «очень разочарован» |
| **TAM / SAM / SOM** | стандарт VC | Размер рынка без фантазий | Воронка рынка |
| **RICE / ICE** | Intercom / др. | Приоритизация бэклога | Score фич |
| **AARRR (Pirate Metrics)** | Dave McClure | Воронка роста | Acquisition → Revenue → Referral |
| **Design Thinking** | IDEO / Stanford d.school | Desirability до feasibility | Empathize → Test |
| **Discovery-Driven Planning** | McGrath & MacMillan | План как набор проверяемых гипотез | Milestones, checkpoints |
| **Business Concept Proofing 3.0** | Bezhovski (2024) | Синтез Stage-Gate + Lean + digital tools | Фазы + LLM/Trends |
| **Kano Model** | Kano | Базовые / performance / delight фичи | Что must-have в MVP |
| **SWOT + PESTLE** | классика | Контекст и риски | Матрицы |
| **Win/Loss analysis** | B2B sales | Почему купили / не купили | Post-launch |
| **Stage-Gate B2B GTM** | SyncGTM 2026 | GTM как stage-gate | ICP → pipeline → validation |

**Для Снегири релевантны все, кроме тяжёлого manufacturing Stage-Gate.** Цифровой продукт = укороченные стадии, акцент на **desirability + unit economics + контент-GTM**.

---

## 2. Stage-Gate · адаптация под Снегири

Классика (Cooper): **Discovery → Scoping → Business Case → Development → Testing → Launch → Post-launch review.**

### Наши стадии и статус

| Stage | Классическое имя | Deliverable | Статус Снегири | Gate критерий |
|-------|------------------|-------------|----------------|---------------|
| **0** | Discovery / Ideation | JTBD, 5–10 интервью, проблема | 🟡 гипотеза в go_nogo | Боль подтверждена ≥5 интервью |
| **1** | Scoping | ICP, конкуренты, MVP scope | 🟡 частично | MVP scope ≤ 12 нед программы + 1 CV |
| **2** | Business Case | Finmodel v4, pricing, LTV/CAC | 🟡 **v4 есть** — нужна валидация + решение по годовому тарифу | LTV/CAC > 1 @ churn 10% |
| **3** | Development | PWA, API, программа | 🟢 v1 есть | Beta работает |
| **4** | Testing / Validation | 10 beta pay, метрики, эталоны | 🔴 не пройден | ≥10 платящих OR LICENSE |
| **5** | Launch | Prod, контент-ритм, Metrika | 🔴 | GO критерии §6 go_nogo |
| **6** | Post-launch | 30/60/90 KPI, churn, win/loss | — | Churn ≤10%, MRR порог |

**Где мы сейчас:** между Stage 3 и 4. **Ошибка последних дней:** прыжок в Stage 5 контента (50 мультиков) без Gate 4.

---

## 3. Lean Startup · Build — Measure — Learn

| Цикл | Снегири · что строим | Что меряем | Learn / pivot |
|------|----------------------|------------|---------------|
| 1 | Лендинг + waitlist | CTR, email | Сообщение резонирует? |
| 2 | 1 бесплатный разбор (stub CV) | % дошедших до конца | Ценность разбора? |
| 3 | Оплата 590 ₽ beta | Free→paid | WTP |
| 4 | 5–10 эталонов + 1 упражнение мультик | QA, «понятно/нет» | Визуал эталона |
| 5 | Программа 6 нед удержания | Churn M2 | Retention hypothesis |

**MVP контента (не 25 мультиков):** S1–S3 + K1–K3 + K6 + **1** эталон с полным QA (rack_hold или jerk).

---

## 4. JTBD · Value Proposition Canvas

### Job stories (рабочие)

1. **Когда** я тренируюсь с гирей дома после работы, **хочу** убедиться, что поясница не в опасности, **чтобы** не бросить через 2 недели из страха.
2. **Когда** врач разрешил ЛФК, **хочу** контроль техники без тренера 20k/мес, **чтобы** делать правильно.
3. **Когда** смотрю YouTube Руднева, **хочу** сравнить **своё** видео с эталоном, **чтобы** понять конкретную ошибку.

### VPC (кратко)

| Customer pains | Gains | Pain relievers | Gain creators |
|----------------|-------|----------------|---------------|
| Страх травмы спины | Уверенность | McGill трек S | CV красная линия |
| Нет тренера | Дёшево vs зал | 590 ₽/мес | Программа 6+ мес |
| YouTube ≠ моё тело | Разбор **моего** видео | Камера в app | Эталон мультик |
| «Не знаю с чего начать» | Лестница | K1→K18 | Фазы |

**Промпт Gemini для углубления VPC:** см. [`snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md) · Сессия A.

---

## 5. Crossing the Chasm · beachhead

| Вопрос | Ответ Снегири |
|--------|---------------|
| **Beachhead** | М 30–50, офис, гиря 16–24 дома, страх поясницы |
| **Whole product** | Программа + разбор + **доверенный эталон** (не stub) |
| **Референс-клиент** | 10 beta из канала Штерн |
| **Не chase** | KMS, похудение, кроссфит-зал |

---

## 6. Ценообразование · Van Westendorp + unit economics

| Метод | Действие | Статус |
|-------|----------|--------|
| **Van Westendorp** | Опрос 4 вопроса в TG (cheap/expensive/too cheap/too expensive) | ❌ не сделан |
| **WTP интервью** | «Купил бы за X?» в custdev | ❌ |
| **Unit economics** | ARPU − COGS − RevShare − infra | 🟡 v3 |
| **Sensitivity** | churn 8% vs 15%, CAC 0 vs 500 ₽ | 🟡 |

**Тарифы:** 590 / 1490 / 3990 — проверить PSM до масштаба.

---

## 7. PMF · Sean Ellis + количественные метрики

| Метрика | Порог PMF | Как мерить |
|---------|-----------|------------|
| Sean Ellis | ≥40% «очень разочарован» если пропадёт | Опрос beta n≥30 |
| Retention M2 | ≥85% paid | Metrika + backend |
| Free→paid | ≥3% | Воронка |
| NPS | ≥30 | После 2 нед использования |

---

## 8. GTM · AARRR для Снегири

```
Acquisition: Stern TG / Дзен / SEO «гира дома спина»
Activation:   онбординг → 1 разбор → aha moment (красная линия на МОЁМ видео)
Retention:    программа фазы, push «день N»
Revenue:      trial → 590 ₽
Referral:     «поделись разбором» (фаза 2)
```

| Канал | Роль | KPI 90 дней |
|-------|------|-------------|
| TG Штерн | trust | 2 поста/нед, CTR на Snegiri |
| TG Снегири | product | 3 поста/нед |
| Дзен | SEO | 2 лонгрида |
| Paid | — | **запрещён** до 30 organic paid |

---

## 9. Kano · MVP feature set

| Фича | Kano | MVP v1 |
|------|------|--------|
| Разбор поясницы (S) | Must | ✅ |
| Программа по дням | Must | ✅ |
| Эталон мультик | Must | 🟡 1 упражнение QA |
| 25 мультиков | Performance | ❌ post-validation |
| OAuth VK | Indifferent | ❌ |
| LLM weekly coach | Delight | ❌ v0.2 |
| 2 гири advanced | Performance | ❌ после base |

---

## 10. Риски · SWOT (сжато)

| S | W | O | T |
|---|---|---|---|
| Бренд-шутка + Штерн | CV stub vs обещание | Домашний фитнес РФ | McGill trademark |
| Программа v3.1 глубокая | Мало subs | LICENSE тренеров | Конкуренты с видео |
| Ниша «гира+спина» | Время основателя | Дзен SEO | Churn короткой программы |

---

## 11. Что нам пригодится · практический чеклист

### Фаза A · Стратегия (1–2 нед) — **сейчас**

- [ ] JTBD + VPC — **Gemini сессия A** + 5 custdev
- [ ] Finmodel v4 (помесячный cashflow) — **Gemini сессия B**
- [ ] Van Westendorp в TG — 50+ ответов
- [ ] GO/NO-GO метрики зафиксированы — уже в go_nogo
- [ ] Kill: не генерить каталог мультиков до Gate 4

### Фаза B · Продукт / desirability (2–3 нед)

- [ ] MVP контента: **1 упражнение** мультик end-to-end (Gemini)
- [ ] Каталог ошибок по школам — **Gemini сессия C** (по 1 slug)
- [ ] A/B: локация, M→F, 1 vs 2 гири — **Gemini сессия D**
- [ ] 5–10 CV-эталонов (LICENSE или самосъёмка)
- [ ] ЮKassa + 10 beta платящих

### Фаза C · Validation (4–6 нед)

- [ ] Sean Ellis PMF опрос
- [ ] Retention M2
- [ ] Metrika цели — `docs/metrika_goals_setup.md`
- [ ] Post-launch review шаблон 30/60/90

### Фаза D · Scale (после GO)

- [ ] Волны мультиков по фазам программы
- [ ] Видео-эталоны (filming_guide)
- [ ] Paid только после 30 organic paid

---

## 12. Модели и формулы (считать)

| Модель | Формула | Наши переменные |
|--------|---------|-----------------|
| **LTV** | ARPU × gross margin × (1 / churn) | 590 ₽, churn 6–15% |
| **CAC** | Marketing spend / new customers | organic ≈ 0 + время |
| **LTV/CAC** | >3 хорошо, >1 минимум | finmodel v4 |
| **Payback** | CAC / (ARPU × margin) | месяцы |
| **Break-even** | Fixed / (ARPU − variable) | subs count |
| **MRR** | Σ active × ARPU | |
| **Churn** | lost / start of period | критично для LTV |

**COGS на разбор:** ~12–25 ₽ (compute + storage) — из issledovanie.

---

## 13. Связь с мультиками (сегодняшняя сессия)

| Ошибка | Правильный gate |
|--------|-----------------|
| 50 лент без QA | Stage 4: 1 упражнение = proof of quality |
| EN / зал / штанга | Spec v2 + errors catalog |
| Пакетная генерация | Lean: one exercise loop |
| Без школ | errors catalog + Gemini сессия C |

**Порядок:** методология (этот doc) → Gemini валидация → A/B пилоты → rack_hold → волны.

---

## 14. Следующий шаг

1. Прогнать **Сессию 0** в Gemini ([`snegiri_gemini_master_sessions.md`](snegiri_gemini_master_sessions.md)) — обзор всего пакета.
2. Сессии A–F по приоритету.
3. Заполнить журнал gate'ов в `go_nogo_master.md` §6.

*«Как по учебнику» = документы + метрики + kill criteria, не объём ассетов.*
