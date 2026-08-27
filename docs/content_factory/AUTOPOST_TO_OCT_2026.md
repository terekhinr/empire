# Автопост до 31.10.2026 (книга у владельца)

**Режим публикации (2026-07-18):** всё **сначала на проверку** админу (`data/auto_publish.json`: `enabled=false`, все `personas`/`rubrics` выключены). Расписание пишет черновики в бота → ты жмёшь «Опубликовать». Автопост в канал не идёт, пока не включишь обратно.

---

## 1. Keep / Cut / Develop

### Gdepar
| | Тема / слот |
|--|-------------|
| **Оставить** | duo practice/evening · classic 15:00 · promo_map пн · book Хошев/история |
| **Убрать** | LLM «Кириллыч, слушай» · блок «О чём писал автор» в классике · >3 хэштега |
| **Развить** | book excerpts из OCR (Богданов, Воеводина, Хошев) · короткие duo без картона |

### Stern
| | |
|--|--|
| **Оставить** | stern_curated 09:30/19:00 · сб technique video · rubric 10:00 **2×/нед** |
| **Убрать** | ежедневные LLM variants (биомеханика/питание/МФР) · weekly_plan/test/recap как ежедневный шум · spy вс |
| **Развить** | офис/дорога/сон/привычка (батч EV-070+) · книжные excerpt позже |

### Lenin
| | |
|--|--|
| **Оставить** | календарь 08:30 · рубрика 12:00 · вечером book/ПСС · вс support |
| **Убрать** | LLM «свободная тема» / марксистский анализ без approve |
| **Развить** | короткие реплики Архивариуса (опционально в note; в TG — чистая цитата) |

### Garden
| | |
|--|--|
| **Оставить** | kizima_lunar |
| **Убрать** | 06:30 «План на день» · LLM 12:00/16:00 · ежедневная луна |
| **Развить** | `garden_curated` Степаныч **Вт+Сб 12:00** |

---

## 2. Частота (МСК) до 31.10

| Канал | Было | Стало | Постов/нед | Запас |
|-------|------|-------|------------|-------|
| **Gdepar** | 3/день | **3/день** (без LLM) | ~21 | duo 139+ · classic 160 · book 27+ |
| **Stern** | до 4/день | **~5–6/нед** | 5–6 | curated 151+ · video 40 |
| **Lenin** | 3/день | **2–3/день** curated | ~14–18 | calendar + rubrics 91 + bedtime 245 |
| **Garden** | 4/день | **3/нед** | 3 | lunar 381 + curated ≥24 |
| **Pension** | — | **вручную** | — | — |

### Сетка по дням

**Gdepar** (без изменений логики, уже curated):
| | 11:00 | 15:00 | 21:00 |
|--|-------|-------|-------|
| Пн | promo_map | classic | duo evening |
| Вт | book pechi | classic | duo evening |
| Ср–Вс | duo practice | classic | duo evening / чт book istoriya |

**Stern:**
| | 09:30 | 10:00 | 15:00 | 19:00 |
|--|-------|-------|-------|-------|
| Пн | — | — | — | curated 1900 |
| Вт | curated 0930 | rubric | — | — |
| Ср | — | — | — | curated 1900 |
| Чт | curated 0930 | rubric | — | — |
| Пт | — | — | — | curated 1900 |
| Сб | — | — | technique video | curated 1900 |
| Вс | curated 0930 | — | — | — |

**Lenin:**
| | 08:30 | 12:00 | 19:00 |
|--|-------|-------|-------|
| Пн–Сб | calendar | rubric | pss / book чередование |
| Вс | calendar | rubric | channel_support |

**Garden:**
| | 12:00 | 20:00 |
|--|-------|-------|
| Вт | garden_curated | — |
| Ср | — | lunar |
| Сб | garden_curated | lunar |

---

## 3. Почему этого хватит до октября

| Пул | Cooldown | Расход | Вердикт |
|-----|----------|--------|---------|
| duo 147+ | 42 д | ~11/нед | хватает с ротацией |
| classic 160 | 56 д | 7/нед | хватает |
| book 27+ | 45 д | 2/нед | впритык → доливаем excerpt |
| stern curated 159+ | 28 д | ~5/нед | с запасом |
| lenin bedtime+rubric | — | ~14/нед | с запасом |
| garden lunar | по дню | 2/нед | с запасом |
| garden curated | 21 д | 2/нед | нужен JSON ≥24 |

---

## 4. Файлы

- Расписание: `content_config.json`
- Автопост: `data/auto_publish.json`
- Новые посты: `data/garden_curated.json` (24), долив `gdepar_duo_curated.json` (155), `stern_curated.json` (167)
- Генерации: `docs/content_factory/generated/`
- Инжест: `scripts/ingest_oct2026_curated_pools.py`

**Пулы vs расход до 31.10:** garden ~62 · stern ~152 · gdepar ~318 · lenin ~318 — при cooldown ротация закрывает; новые duo/stern/garden долиты.

**После правок:** `systemctl restart empire_main` (уже перезапущен 2026-07-18).

**Важно:** у новых duo/stern jpg может не быть на диске — в `auto_publish` для duo `require_image=false`; stern по-прежнему хочет картинку на matrix-слотах (fal/очередь как раньше).
