# Gemini · Сессия J · провал 50 лент · negative prompts

**Дата:** 2026-07-13  
**Автор:** Cursor (Auto)

---

## 1. Классификация дефектов

| Категория | Частота | Корень | Fix |
|-----------|---------|--------|-----|
| Штанга/стойки в кадре | высокая | `industrial gym` без FORBIDDEN | FORBIDDEN + brief location |
| EN подписи (ST, DRIVE) | высокая | старый мастер-промпт | labels_ru only |
| 1 vs 2 гири | средняя | нет tier в brief | tier base + equipment block |
| M ≠ F хореография | высокая | F без ref M | ref M обязателен |
| Локти в стороны (jerk/rack) | средняя | нет schools catalog | errors_catalog + technique block |
| Watermark Gemini | низкая | — | QA reject |

**Спасти из 50:** нет для prod. Архив `_draft/` / антипримеры для J. Перегенерация с нуля дешевле QA.

---

## 2. TOP-15 negative prompts (EN, в каждый image prompt)

```
NO barbell, NO barbell plates, NO squat rack, NO power rack, NO bench press
NO dumbbells, NO cable machine, NO commercial gym logos
NO English text on image, NO Latin exercise labels
NO two kettlebells unless tier advanced explicitly stated
NO left hand kettlebell on one-arm exercises (RIGHT hand only)
NO elbows flared 90 degrees on rack or jerk (crossfit style)
NO motivational posters with faces on walls
NO Nike Adidas StrongFirst logos on clothing
NO colored equipment except single #FF3300 error line
NO multiple error red lines, NO decorative red
NO woman with different choreography than man reference
NO smiling stock fitness model aesthetic, NO pastel colors
NO watermark, NO Gemini logo
```

---

## 3. TOP-10 mandatory positive lines (EN)

```
EXACTLY ONE 16kg cast iron kettlebell (unless advanced tier: TWO)
All panel labels in RUSSIAN Cyrillic CAPS from brief labels_ru
Black background #000000, white figure, single #FF3300 error line only
Black t-shirt, white bullfinch-on-kettlebell logo chest 8-10cm
INDUSTRIAL GYM empty concrete metal walls OR home_room per brief
White CV skeleton overlay on athlete
Panel ERROR: one school-sourced mistake with red line on anatomical zone
For rack/jerk: elbow tucked to torso / iliac crest, NOT wings
ATHLETE: repeat approved M strip choreography when generating F
Horizontal 1920x1080, 3-6 equal panels left to right
```

---

## 4. Почему пакет F без M обречён

Image models **не держат** kettlebell count, hand side, panel layout между запросами. Единственный стабильный якорь — **image reference** утверждённого M. Без ref модель «додумывает» вторую гирю и другие углы.

---

## 5. Минимальный пилот (вместо 50)

1. `rack_hold` M → QA → F  
2. `jerk` M → QA → F  
3. A/B `swing` industrial vs home (M only)

= **6–8 картинок** для Gate, не 50.

---

*Использовать в gemini.google.com вместе с output `render_comic_prompt.py`.*
