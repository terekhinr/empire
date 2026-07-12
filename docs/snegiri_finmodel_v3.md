# Finmodel v3 · Снегири · ответ Gemini + аудит Cursor

**Дата:** июль 2026 · промпт: [`snegiri_go_nogo_master.md`](snegiri_go_nogo_master.md) §7  
**Вердикт Cursor:** **PIVOT** (согласен с Gemini) — не «убить SaaS», а **медиа-подписка + инструмент**, CV с **жёсткой квотой**. **NO-GO** для чистого «безлимитного AI-разбора» при 590 ₽.

---

## A. Финансовые сценарии (из Gemini)

| Метрика | M1 | M3 | M6 | M12 | Комментарий |
|---------|----|----|----|-----|-------------|
| **NO-GO** | | | | | |
| Users | 15 | 25 | 30 | 20 | Стагнация |
| MRR | 8 850 | 14 750 | 17 700 | 11 800 | |
| Churn | 15% | 12% | 15% | 18% | |
| Cashflow | -55k | -5k | +2k | -1k | |
| LTV (GM) | 1 800 | 2 250 | 1 800 | 1 500 | |
| **BASE** | | | | | |
| Users | 20 | 60 | 120 | 250 | |
| MRR | 11 800 | 35 400 | 70 800 | 147 500 | Paid с M5 |
| Churn | 8% | 6% | 5% | 4% | |
| Cashflow | -50k | +10k | +25k | +65k | ~200k к M12 |
| **GO** | | | | | |
| Users | 30 | 100 | 250 | 600 | |
| MRR | 17 700 | 59 000 | 147 500 | 354 000 | |
| Churn | 6% | 5% | 4% | 3.5% | |
| Cashflow | -40k | +25k | +70k | +180k | ~800k к M12 |

*ARPU 590 ₽; mix годового (332 ₽/мес) в модели **не учтён** — реальный ARPU скорее **520–550 ₽**.*

---

## B. Unit economics (Gemini)

| Статья | ₽ | % |
|--------|---|---|
| ARPU | 590 | 100% |
| Налог + эквайринг | -41 | 7% |
| COGS CV (8×18) | -144 | 24.4% |
| RevShare 20% | -81 | 13.7% |
| **Gross margin** | **324** | **54.9%** |
| LTV @ churn 4% | 8 100 | |
| Max CAC (LTV/3) | 2 700 | |

**Проверка RevShare:** если 20% от **gross** (590) → -118 ₽, margin **287 ₽**. Уточнить в договоре LICENSE.

---

## C. Break-even

| | |
|--|--|
| CAPEX | 55 000 ₽ → ~170 user-months маржи; при 50 users ≈ **3.5 мес** |
| Cash BE | **~10 users** (хостинг ~3k) |
| Economic BE (120k ₽/мес opportunity) | **~370 users** |

---

## D–I. Кратко

- **Sensitivity:** при churn 8% LTV GM ≈ 4 050 ₽ → max CAC trial **135–270 ₽**
- **Funnel:** 10k views → **4–5 платящих** (0.04–0.05%). На 100 users нужно **~250k целевых просмотров**
- **PIVOT:** подписка = **система + комьюнити**; CV = фича с **квотой 5–8/мес**
- **STOP:** CV <70% usable, COGS >40% margin, churn 12–15% @ 50 users

---

## J. Слепые зоны CV и серверов (ответ на вопрос)

**Да, слепые зоны есть.** Gemini заложил 18 ₽/разбор, но **не моделировал пик и архитектуру as-is**.

### Что в коде сейчас (факт)

| | Реальность |
|--|-----------|
| CV | MediaPipe **CPU**, sync в HTTP-запросе — **нет очереди** |
| Fallback | Heuristic по размеру файла (не CV) |
| Видео | Сохраняется на диск **без TTL** |
| Лимиты | Min 1 KB; **нет** max длины/размера/квоты на сервере |
| Free tier | 1 разбор в `localStorage` — **обходится** новой сессией |

### Слепые зоны, которые ломают экономику на пике

| # | Риск | Пиковый сценарий | Удар по P&L |
|---|------|------------------|-------------|
| **1** | **Sync analyze** | Пост Stern → 50 одновременных upload | Таймауты, падение VPS, **0 конверсии** |
| **2** | **Heavy user** | 30 разборов/мес × 60 сек 1080p | COGS **×3–4** vs модели |
| **3** | **Storage** | 10 MB × 1000 users × 8 мес | **+50–100 GB**, не в COGS |
| **4** | **Egress/ingress** | 200 upload/день × 15 MB | Трафик VPS, не учтён |
| **5** | **Failed retries** | Плохой ракурс → 3 пересъёмки | **3× compute** без revenue |
| **6** | **GPU migration cliff** | Переход на cloud GPU для «настоящего» CV | 18 ₽ → **40–80 ₽**/job |
| **7** | **model_complexity=2** | Точность ↑, CPU ×2–3 | Маржа ↓ или очередь часами |
| **8** | **Abuse / free** | Новый session_id = новый free | COGS без ARPU |
| **9** | **Worker RAM** | 5 parallel MediaPipe на 2 GB VPS | OOM kill |
| **10** | **Night batch** | Нет — всё inline | Пик = дневной пост |

### Оценка COGS по архитектурам (30 сек, 720p, ~100 кадров pose)

| Архитектура | ₽/разбор | Комментарий |
|-------------|----------|-------------|
| **A. CPU VPS** (текущий путь) | **3–8** | Дешево, но **пик ломает** без queue |
| **B. RTX 4060 local worker** | **2–5** + аморт. железа | Gemini OK для dev; prod = SPOF |
| **C. Cloud GPU spot** | **25–60** | Модель Gemini 18 ₽ **оптимистична** |
| **D. Heuristic only** | **~0** | Маржа OK, **продукт = обман** vs лендинг |

**Вывод:** при **безлимите** и **cloud GPU** SaaS @ 590 ₽ **не сходится**. При **квоте 8 + CPU queue + cap 45 сек 720p** — **324 ₽ margin достижима**.

### Пиковая нагрузка (stress math)

Допустим пост с **10k views**, funnel Gemini → **50 trial uploads/день**:

```
50 × 15 MB upload     ≈ 750 MB ingress
50 × ~5 sec CPU each  ≈ 250 sec CPU (OK на 4 vCPU)
50 concurrent         ≈ FAIL на sync uvicorn × 1 worker
50 × 15 MB storage    ≈ 750 MB/день → 22 GB/мес без cleanup
```

**Trigger масштабирования:** >**30 analyze/час** или p95 latency >**60 сек** → queue + 2-й worker, иначе не paid traffic.

---

## K. Рекомендация Cursor (синтез)

| | |
|--|--|
| **GO/NO-GO проекта** | **PIVOT**, не чистый SaaS и не kill |
| **Продукт** | «Снегири + Штерн» = **подписка на программу 6–12 мес**; CV **8 разборов/мес** (hard cap API) |
| **Dev** | **Freeze** фич; **2 нед** только: квота, queue, video cap, storage TTL |
| **GTM** | Воронка E **до** paid; цель **12% trial→paid** на **500** cold visits |
| **Kill** | <10 paying @ 01.11 **или** COGS >40% margin @ 30 users |

### Hybrid (лучше чем «только PDF»)

| Слой | Монетизация |
|------|-------------|
| PDF / лидмагнит | 0 ₽ → email |
| Подписка 590 ₽ | Программа + 8 CV + архив |
| Закрытый TG 990 ₽ | Опционально tier 2 (без CV лимита — **не** делать) |

---

## L. Чеклист до paid traffic (тех)

- [ ] `max_video_sec=45`, `max_mb=25`
- [ ] Server quota: `8 analyzes/month/user` (subscription)
- [ ] RQ/Celery queue, async response «готово через push/poll»
- [ ] TTL uploads 30 days
- [ ] Rate limit: 3 analyze/hour/session
- [ ] Session-bound free trial (server-side)
- [ ] Load test: 20 concurrent → p95 < 90 sec

---

## M. Связанные документы

- [`snegiri_go_nogo_master.md`](snegiri_go_nogo_master.md)
- [`snegiri_program_retention_v1.md`](snegiri_program_retention_v1.md)
- [`snegiri_finmodel_v2_strategy.md`](snegiri_finmodel_v2_strategy.md) §4.4
