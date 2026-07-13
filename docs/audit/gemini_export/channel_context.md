# Контекст каналов Empire (для аудита Gemini)

**Дата экспорта:** 2026-07-13  
**Источник:** `empire.db` → `post_drafts` where `status='published'`  
**Всего published:** 828 (2026-05-07 … 2026-07-13)

---

## Каналы в Telegram

| persona_key | Название | Слотов/день (МСК) |
|-------------|----------|-------------------|
| gdepar | Где пар? | 3 (11, 15, 21) |
| stern | снегири НЕ ГИРИ | 4 (09:30, 10:00, 15:00 сб, 19:00) |
| lenin | ЛЕНИН | 3 (08:30, 12, 19) |
| garden | Сеем, пашем | 4 (06:30, 12, 16, 20) |
| pension | На пенсию НИКОГДА | заморожен |

---

## Статистика published (полная история)

| persona | n | avg_len | auto | approved | with_img |
|---------|---|---------|------|----------|----------|
| stern | 256 | 1043 | 54 | 188 | 242 |
| garden | 245 | 647 | 63 | 164 | 242 |
| gdepar | 158 | 792 | 41 | 99 | 153 |
| lenin | 155 | 919 | 31 | 107 | 143 |
| pension | 14 | 1392 | 0 | 14 | 1 |

**Очередь:** pending 359 · rejected 64

---

## Автофлаги клише (pattern_flags.tsv)

| флаг | count |
|------|-------|
| stern_hashtag_heavy (>5 #) | 190 |
| gdepar_kirilych (текст) | 100 |
| garden_weather | 84 |
| gdepar_gdepar_link | 76 |
| lenin_pss | 93 |
| garden_lunar | 52 |
| gdepar_classic_banya | 41 |
| lenin_calendar | 40 |
| stern_joints | 63 |
| stern_mamatov | 21 |

---

## Режим контента (июль 2026, после правок)

| Канал | Curated | LLM / legacy |
|-------|---------|--------------|
| **gdepar** | duo, classic, book, promo — 100% слотов | старые 50% корпуса — LLM «Кириллыч» |
| **stern** | matrix 09:30/19:00, rubrics 10:00, video сб | legacy [Рутина] LLM; план/тест недели — LLM |
| **lenin** | рубрики, ПСС, сказка, календарь (prebuilt) | 15× «Свободная тема» в истории |
| **garden** | луна 20:00, промо вс | 58× «План на день», LLM 12/16 |
| **pension** | — | владелец сам |

---

## Бизнес-роли

| Канал | Монетизация | Приоритет |
|-------|-------------|-----------|
| gdepar | gdepar.ru, Premium, CPA | **Флагман B2B** |
| pension | книга 299₽, YouTube | **Флагман бренд** (заморожен TG) |
| stern | snegirinegiri.ru, neverretire | Спутник |
| garden | PDF, ВК/Дзен | Спутник |
| lenin | Stars | Хобби |

---

## Персоны

**gdepar:** Михалыч + Кириллыч — разговорный русский, без «священнодействия». Curated JSON.

**stern:** Прагматик, McGill, офисник 30–50. Не помост/WKSF. Curated + видео чемпионов.

**lenin:** Архивный тон, ПСС blockquote, календарь из файла.

**garden:** Степаныч, Кизима луна — curated; остальное пока LLM.

---

## Ограничения данных

- Нет просмотров/ER в analytics.db
- ER оценивать по качеству текста и отраслевым нормам

См. `gemini_PROMPT_FULL_AUDIT_JUL2026.txt`, `full_audit_stats.json`
