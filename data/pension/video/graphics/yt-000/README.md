# YT-000 · Графика для монтажа (1920×1080 PNG)

**Регенерация:** из корня репозитория

```bash
MPLCONFIGDIR=.matplotlib_cache ./venv/bin/python scripts/generate_yt000_graphics.py
```

**Стиль:** тёмный фон `#0d1117`, золото — РФ/акцент, красный — UK/риск, синий — OECD.

**Водяной знак на слайдах:** `НА ПЕНСИЮ НИКОГДА` (бренд канала/книги).  
**neverretire.ru** — только в озвучке финала и в описании ролика (трафик на книгу), не на каждом графике.

**Вёрстка (v2):** заголовок → график → **insight-полоса** (пояснение одной строкой) → источник + бренд. Без текста поверх графика. **Флаги** стран — `assets/flags/` (flagcdn, кэш при генерации).

**AI-картинки (B-roll, не графики):** промпты — [`image_prompts.md`](image_prompts.md) · конфиг — [`images_config.json`](images_config.json) · **23 PNG** в [`images/`](images/) (см. `images/manifest.json`).

Генерация:

```bash
./venv/bin/python scripts/generate_yt000_images_gemini.py              # только Gemini
./venv/bin/python scripts/generate_yt000_images_gemini.py --provider auto  # Gemini → Fal при 429
./venv/bin/python scripts/generate_yt000_images_gemini.py --provider fal --force
```

---

## Карта «файл → таймкод сценария»

| Файл | Когда вставить | Содержание |
|------|----------------|------------|
| `08_demography_workers_per_pensioner.png` | Крючок 0:00–1:30 | 9 → 2.5 → 1.8 работающих на пенсионера |
| `12_stereotype_vs_median.png` | Блок 6, стереотип | Хвост vs медиана |
| `13_hemingway_quote.png` | Блок 7, пауза | Цитата Хемингуэя |
| `05_oecd_old_age_poverty.png` | Блок 6 / миф 18:00 | 11,5% vs 14,8% vs 17,2% |
| `09_eu_gender_pension_gap.png` | Блок 6 | −24,5% пенсия женщин ЕС |
| `01_ipk_cost_russia.png` | Блок 1Б баллы | Рост цены балла 2019–2026 |
| `02_uk_winter_fuel_payment.png` | Блок 6 UK | 10,6 → 1,3 млн WFP |
| `03_uk_cold_mortality_episodes.png` | Блок 6 UK | 421 / 493 / 1630 по эпизодам |
| `04_uk_winter_dashboard.png` | Блок 6 UK (один слайд) | 2544 + 11% + 13% |
| `06_us_retirement_accounts_55_64.png` | Блок 1Б / США | 57% / 43% donut |
| `07_oecd_replacement_rates.png` | Блок 4 покупательная сила | 43% / 52% / 57% |
| `10_table_countries_one_mechanism.png` | Блок 2–3 или 1Б | Сводная таблица 6 стран |
| `11_infographic_nowhere_to_run.png` | Финал 25:30 | «Ехать некуда» |
| `10_table_countries_one_mechanism.png` | Перед финалом | Повтор при необходимости |

---

## Монтаж

- Формат: **PNG**, ~1920×1080 (после `bbox_inches=tight` может чуть отличаться — в Davinci/Premiere масштабировать до frame).
- Длительность на экране: **5–8 сек** на график, **10–12 сек** на таблицу.
- Анимация: лёгкий **zoom-in 102%→100%** или появление opacity 0→100% — по вкусу.
- Субтитры: дублировать ключевую цифру голосом ведущего.

---

## Источники (на слайдах уже есть footer)

См. `data/pension/scripts/pension_yt/yt-000_sources.md`
