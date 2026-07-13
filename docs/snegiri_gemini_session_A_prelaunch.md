# Gemini · Сессия A · предзапуск · playbook v1

**Дата:** 2026-07-13  
**Автор:** Cursor (Auto) — для сверки в gemini.google.com  
**База:** [`snegiri_product_prelaunch_methodology.md`](snegiri_product_prelaunch_methodology.md)

---

## 1. Пропущенные методики (добавить)

| Методика | Зачем Снегири |
|----------|---------------|
| **Regulatory / 152-ФЗ** | Видео пользователя на сервере — политика, согласие, TTL |
| **Cohort analysis** | Retention по неделе входа, не только churn % |
| **CAC payback по каналу** | Stern TG vs Дзен vs SEO отдельно |
| **Competitive teardown** | YouTube бесплатно vs Fitify vs «тренер в зале» |
| **Whole Product (Moore)** | Программа + 1 эталон + (опц.) лицо тренера |
| **Fake door / smoke test** | Кнопка «Купить» до ЮKassa — CTR намерения |
| **Concierge MVP** | 5 пользователей — разбор вручную в TG до автоматизации |
| **North Star Metric** | «Активных недель с ≥1 разбором» vs vanity MRR |

---

## 2. Stage-Gate · 7 gate'ов Снегири

| Gate | Deliverable | Сейчас | Не сделано |
|------|-------------|--------|------------|
| **G0 Discovery** | JTBD, 5 интервью, боль | 🟡 гипотеза | Интервью, Van Westendorp |
| **G1 Scoping** | ICP, MVP scope | 🟡 | Конкурентная матрица 1 стр |
| **G2 Business Case** | Finmodel v4, pricing | 🟡 v4 есть | Решение годового тарифа; валидация churn |
| **G3 Build** | PWA + программа | 🟢 | CV hardening (queue, cap) |
| **G4 Validate** | 10 pay OR LICENSE | 🔴 | 0 paying; K0 в работе |
| **G5 Launch** | Prod + ритм + Metrika | 🔴 | DNS prod, 8 постов/мес |
| **G6 Scale** | 30+ pay, MRR 15k | — | — |

**Почему 50 мультиков = ошибка Stage-Gate:** это Stage **5 контент** без **G4** (платящие + эталон quality). Cooper: «kill early» — мы пропустили testing gate и купили manufacturing до product-market fit.

---

## 3. Lean · 5 гипотез на 4 недели

| # | Мы верим, что… | Измерим | Успех | Pivot если |
|---|----------------|---------|-------|------------|
| H1 | Офисник заплатит 590 ₽ за **разбор своего** видео | trial→paid | ≥5% на 200 визитах | <2% → продавать только PDF программу |
| H2 | Программа 6+ нед снижает churn | M2 retention paid | ≥85% | <75% → укоротить обещание / добавить push |
| H3 | Stern TG даёт трафик без paid | CTR пост→сайт | ≥3% клик | <1% → Дзен SEO primary |
| H4 | 1 мультик rack_hold понятен без тренера | опрос 10 users «понятно 1–5» | ≥4 среднее | <3 → текстовые cue важнее картинки |
| H5 | Industrial gym эталон не путает «я дома» | A/B + 5 вопросов custdev | ≥70% «не мешает» | home_room побеждает |

---

## 4. Value Proposition Canvas · beachhead

**Beachhead:** мужчина 30–50, офис, гиря 16–24 дома, страх поясницы на свинге.

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Тренироваться после работы без зала | Страх травмы спины | Уверенность |
| Понять «правильно ли я делаю» | YouTube ≠ моё тело | Контроль без тренера |
| Не бросить через 2 недели | Нет программы на год | Прогресс виден |
| Начать с безопасной базы | «Купил гирю — что дальше?» | Лестница S→K |

### Value map

| Pain relievers | Gain creators |
|----------------|---------------|
| McGill трек S перед гирей | Красная линия на **моём** видео |
| 590 ₽ vs 20k тренер | Программа по дням 6+ мес |
| Эталон мультик по школам | Один снаряд, понятные фазы RU |
| Честный лимит 8 разборов | Школа Штерна / снегири-мем |

---

## 5. Kano · MVP

| Фича | Kano |
|------|------|
| Программа по дням S+K | **Must** |
| CV разбор (квота) | **Must** |
| 1 мультик QA | **Must** |
| ЮKassa | **Must** |
| Metrika | **Must** |
| 25 мультиков | Performance (post-validate) |
| OAuth VK | Indifferent |
| LLM weekly coach | Delight (v0.2) |
| 2 гири advanced | Performance (post-S) |
| Видео тренера LICENSE | Performance (trust) |

---

## 6. GTM 90 дней (без paid до 30 organic paid)

| Нед | Acquisition | Activation | Retention | KPI |
|-----|-------------|------------|-----------|-----|
| 1–2 | 2 поста Stern + 1 Дзен черновик | Бесплатный разбор live | — | 50 визитов, 10 trial |
| 3–4 | 3 поста Snegiri, кейс разбора | Email/onboarding | Программа день 1–7 | 3 paying |
| 5–6 | Дзен публикация SEO | CTA 590 ₽ | Push неделя 2 | 10 paying |
| 7–8 | Повтор лучшего поста | A/B лендинг copy | Churn M2 замер | 15 paying |
| 9–12 | 2 Дзен + Stern ритм | Реферал «поделись» (опц.) | Новые фазы K | 25–30 paying |

**Paid ads:** запрет до 30 organic paid **и** trial→paid ≥8%.

---

## 7. Что НЕ делать (ловушки соло-основателя)

1. 25 мультиков до 3 paying  
2. Rebrand / второй домен  
3. OAuth / LLM coach до retention  
4. Реклама 80k/мес «как в finmodel base»  
5. Книга до PMF  
6. YouTube-канал как блокер  
7. GPU / «настоящий» CV до квоты и queue  
8. 70 видео-эталонов до LICENSE переговоров  
9. EN-версия до 100 RU paid  
10. Пакетная генерация F без M  
11. Оптимизм churn 4% в планах  
12. Игнор 152-ФЗ на видео  

---

## 8. Pre-launch playbook Снегири v1 · оглавление

| § | Раздел | Суть |
|---|--------|------|
| 1 | **ICP & JTBD** | Офисный гиревик, страх спины; job = контроль техники дома |
| 2 | **VPC & positioning** | Шутка снегири + жёсткая биомеханика; vs YouTube |
| 3 | **Stage-Gate статус** | Между G3 и G4; kill 50 мультиков |
| 4 | **Finmodel & pricing** | v4 канон; годовой тариф — решить |
| 5 | **Unit economics** | Margin ~150; LTV @10% churn = 1.5k |
| 6 | **MVP scope** | Программа + 8 CV + 1 мультик |
| 7 | **Content GTM** | Stern→Snegiri→trial; 8 постов/мес |
| 8 | **Validation pack** | 5 custdev, ЮKassa, Metrika, 10 beta |
| 9 | **Comic/canon** | strategy_v2, briefs, errors, A/B |
| 10 | **LICENSE K0** | Тренеры / самосъёмка; дедлайн 01.11 |
| 11 | **Legal & privacy** | McGill формулировки, 152-ФЗ, TTL видео |
| 12 | **GO/NO-GO 01.11** | 30 pay / MRR 15k / churn ≤10% |

---

*Сверь с Gemini: что добавить/убрать — правки в этот файл или комментарий основателю.*
