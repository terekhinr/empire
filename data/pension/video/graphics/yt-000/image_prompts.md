# YT-000 · Промпты для генерации картинок (B-roll / метафоры)

**Назначение:** иллюстрации к пилоту, которые **не заменяют** графики (`01`–`13.png`), а дают эмоцию, контраст, метафору.  
**Формат:** 16:9, **1920×1080** (или 1344×768 под Imagen — upscale в монтаже).  
**Точные рамки кадра, safe zone, кроп:** [`image_frame_specs.md`](image_frame_specs.md) — **по одному промпту на кадр с размерами**.  
**Связь со сценами:** `yt-000_pilot_full_package.md`, Часть 1 · озвучка: `yt-000_vo_for_recording.md`.

---

## 0. Два визуальных режима (не смешивать в одном кадре)

### A · Документальный B-roll (основной для пилота)

Используй для сцен 01–02, 06–07, 16–18, 21–24.

```
Cinematic documentary still, 16:9, photorealistic but subdued, desaturated cold color grade,
slate blue and charcoal shadows, subtle film grain, no smile stock-photo aesthetic,
no readable text, no logos, no watermarks, no celebrity faces, Russian/European setting
when people shown — generic not identifiable, dramatic natural or office lighting,
high detail, shallow depth of field optional, mood: financial anxiety not horror porn
```

**Negative (добавлять ко всем A):**
```
cartoon, anime, 3d render, illustration, bright saturated colors, happy retirement advertising,
beach resort commercial, lens flare spam, text, letters, numbers on screen, logo, watermark,
gore, violence, distorted hands, extra fingers, blurry face
```

### B · Метафора / схема (опционально, 5–8 кадров)

Упрощённая **editorial infographic** в духе The Economist / Bloomberg — не мультик Бороды.

```
Editorial financial illustration, flat design, dark navy background #0d1117,
gold accent #d4a853 and muted red #f85149, clean geometric shapes, no characters,
no text labels, 16:9, minimal detail, vector-like clarity, serious tone
```

**Negative B:**
```
photorealistic, photograph, cute, playful, 3d pixar, cluttered, text, watermark, comic strip
```

### C · Линейный мультик (только если вставляете вставки «как в демо»)

См. `scenes_4.json` + `iosif_boroda_ref.png`. Для пилота **не обязателен** — пилот тяжелее по тону, чем демо.

---

## 1. Карта: сцена → картинка

| ID | Сцены | Зачем | Режим |
|----|-------|-------|-------|
| IMG-01 | 01–02 | Реклама «заслуженный отдых» | A |
| IMG-02 | 02 | Обрыв иллюзии | A или B |
| IMG-03 | 04 | Заморозка накоплений | B |
| IMG-04 | 06 | Бисмарк / индустриальный век | A |
| IMG-05 | 07 | PAYG-конвейер | B |
| IMG-06 | 07 | Пустой сейф / нет «ваших» денег | A |
| IMG-07 | 08 | Баллы как жетоны / чужая таблица | B |
| IMG-08 | 11 | Глобус / старение планеты | B |
| IMG-09 | 12 | Япония, окно, пустой стол | A |
| IMG-10 | 13 | Протесты, пенсионный возраст | A |
| IMG-11 | 14 | Корзина vs квитанции | A |
| IMG-12 | 16a | «Богатый дед» — яхта/круиз | A |
| IMG-13 | 16b | «Старушка» — подъезд / лекарства | A |
| IMG-14 | 17a | UK: пальто дома, термостат | A |
| IMG-15 | 17b | UK: счётчик / холодное окно | A |
| IMG-16 | 20 | Чемоданы, одинакий коридор | A |
| IMG-17 | 21 | Четыре стены (метафора) | B |
| IMG-18 | 22 | Хемингуэй: постепенно → обрыв | A или B |
| IMG-19 | 24a | Зал, штанга | A |
| IMG-20 | 24b | Ноутбук, график (без цифр) | A |
| IMG-21 | 24c | Огород / земля | A |
| IMG-22 | 25 | Паспорта на столе, карта мира | A |
| IMG-23 | 27 | Заставка-атмосфера канала | B |

**Не генерировать:** UK цифры, OECD, таблицы стран, donut USA — уже есть PNG.

---

## 2. Промпты (EN для Imagen / Midjourney / Flux / DALL·E)

К каждому промпту дописывай блок **Style A** или **Style B** из раздела 0.

---

### IMG-01 · Реклама пенсии (сц. 01)

**Prompt:**
```
Wide shot of a generic silver-haired man in beige linen clothes walking alone on an empty
Mediterranean beach at golden hour, calm sea, soft warm light like a insurance TV commercial,
peaceful retirement fantasy mood, back or three-quarter view so face is not recognizable,
no text, no logo, cinematic 16:9
```

**Вариант «перегиб» (для монтажа с глитчем):**
```
Same beach retirement commercial scene but slightly uncanny: oversaturated warmth,
too perfect, subtle artificial look, hint of unease, still no text
```

---

### IMG-02 · Актуарная таблица / обман (сц. 02)

**Prompt (A):**
```
Close-up of an anonymous insurance actuary desk: blurred spreadsheet on monitor,
mortality life table printout, calculator, cold office light, hands of middle-aged clerk
not showing face, mood: calculating human lifespan as numbers, documentary, desaturated
```

**Prompt (B):**
```
Split image: left half bright beach silhouette, right half dark spreadsheet grid fading to black,
sharp vertical tear between them, editorial metaphor for pension marketing vs accounting, no text
```

---

### IMG-03 · Заморозка 2014 (сц. 04, парадокс)

**Prompt (B):**
```
Frozen piggy bank inside clear ice block on dark desk, single crack through ice,
gold coin visible but trapped, metaphor for frozen pension savings, minimal composition,
dark navy background, dramatic side light
```

---

### IMG-04 · Бисмарк / 1889 (сц. 06)

**Prompt (A):**
```
Historical industrial atmosphere evoking 1880s Germany: smoky factory chimneys, workers silhouettes
leaving brick factory gate at dusk, sepia-desaturated documentary tone, NOT a portrait of any
real historical figure, wide establishing shot, 16:9, grain
```

---

### IMG-05 · PAYG-конвейер (сц. 07)

**Prompt (B):**
```
Abstract conveyor belt made of silhouetted human figures: young workers at bottom feeding
coins upward to elderly figures at top, factory metaphor for pay-as-you-go pension system,
dark background, gold coins, clean editorial illustration, no text, arrows implied not labeled
```

---

### IMG-06 · Не ваш сейф (сц. 07)

**Prompt (A):**
```
Open empty bank safe deposit box interior, bare metal, single dim bulb, no money inside,
lonely composition, metaphor for pension promise without savings, cool blue shadows,
photorealistic documentary still
```

---

### IMG-07 · Баллы вместо денег (сц. 09)

**Prompt (B):**
```
Glass jar filled with generic poker chips or tokens instead of coins, label area blank,
government building silhouette blurred in background, metaphor for pension points not cash,
dark moody lighting, editorial still life, no readable text
```

---

### IMG-08 · Глобальное старение (сц. 11)

**Prompt (B):**
```
Stylized transparent globe showing disproportionate grey elderly population icons vs few small
child icons, demographic imbalance visualization, dark blue space background, minimal flat design,
serious infographic aesthetic, no country names, no numbers
```

---

### IMG-09 · Japan madogiwa (сц. 12)

**Prompt (A):**
```
Japanese corporate office interior: elderly office worker sitting alone by large window,
empty desk with no work, staring outside, grey daylight, quiet humiliation mood,
wide shot from behind, face not visible, realistic, desaturated, 16:9
```

---

### IMG-10 · Протест пенсионного возраста (сц. 13)

**Prompt (A):**
```
Street protest in European city, crowd from behind, raised fists and blank placards without text,
smoke or evening light, pension reform atmosphere, photojournalism style, no flags readable,
no identifiable politicians, dynamic but not violent
```

---

### IMG-11 · Покупательная способность (сц. 14)

**Prompt (A):**
```
Kitchen table top view: small modest grocery pile (bread, medicine box without labels, utilities
bill envelope with blank paper), elderly person's thin hands counting coins, shallow depth of field,
muted colors, documentary poverty not melodrama, no readable text
```

---

### IMG-12 · Стереотип: «богатый пенсионер» (сц. 16a)

**Prompt (A):**
```
Wealthy retired couple on small yacht deck, champagne glasses without brand labels, sunny Mediterranean,
luxury travel magazine look but slightly distant cold color grade to feel like rare tail of distribution,
faces turned away or out of focus, 16:9
```

---

### IMG-13 · Стереотип: «старушка из подъезда» (сц. 16b)

**Prompt (A):**
```
Elderly woman in worn coat sitting on wooden bench in dim Soviet-style apartment building stairwell,
plastic bag with groceries, cold greenish light from window, lonely realistic documentary photo,
face partially obscured, dignified not caricature, no text
```

---

### IMG-14 · UK fuel poverty — внутри (сц. 17)

**Prompt (A):**
```
Elderly person wearing winter coat and scarf indoors sitting in armchair, breath visible in cold room,
unlit radiator, cup of tea on side table, British modest living room, soft grey daylight from window,
empathetic documentary tone, not sensational, face in profile not sharp portrait
```

---

### IMG-15 · UK — счётчик / окно (сц. 17)

**Prompt (A):**
```
Close-up of UK-style electricity meter or thermostat on cracked paint wall, finger hesitating to turn dial,
cold blue ambient light, shallow depth of field, metaphor for heating cost, no readable numbers on display
```

---

### IMG-16 · «Уеду — будет нормально» (сц. 20)

**Prompt (A):**
```
Airport departure board area blurred in background, foreground: two identical cheap suitcases and
passport covers without visible country names, mood: emigration does not escape math, cool tones,
still life composition, documentary
```

---

### IMG-17 · Четыре стены (сц. 21)

**Prompt (B):**
```
Four crumbling walls closing in on a tiny empty chair in center, each wall texture different:
crowd silhouettes, inflation arrow shape, parliament dome shape, turkey feather shape abstract,
metaphor for pension trap, dark editorial illustration, no text
```

---

### IMG-18 · Хемингуэй — постепенно, потом внезапно (сц. 22)

**Вариант A (фото-метафора):**
```
Landscape with long gentle cracked asphalt road leading to abrupt cliff edge, fog, desaturated,
metaphor for gradual then sudden collapse, cinematic wide 16:9, no people, no text
```

**Вариант B (атмосфера; цитату на экране — `13_hemingway_quote.png`):**
```
1920s Paris cafe interior empty table, one chair, glass of water, noir high contrast black and white,
rain on window, mood Ernest Hemingway, no visible book title, no text
```

---

### IMG-19 · Тело (сц. 24a)

**Prompt (A):**
```
Small gritty gym interior: barbell on floor, chalk dust, single overhead bulb, no people,
metaphor for body as primary asset, masculine documentary aesthetic, desaturated, 16:9
```

---

### IMG-20 · Кэшфлоу / навык (сц. 24b)

**Prompt (A):**
```
Home desk at night: laptop showing blurred green-red chart without readable numbers, notebook,
pen, coffee, disciplined worker mood, blue screen glow on dark room, not crypto bro aesthetic,
realistic still life
```

---

### IMG-21 · Земля (сц. 24c)

**Prompt (A):**
```
Hands planting seedlings in dark soil, suburban small garden bed, early spring grey sky,
honest physical work metaphor, close-up, documentary natural light, dirt under fingernails,
no face
```

---

### IMG-22 · Ехать некуда (сц. 25)

**Prompt (A):**
```
World map print on old desk covered with multiple rejected visa/stamp pages blank,
compass, worn passport, metaphor: no exit from demographic math, top-down still life,
muted sepia-cold grade, no readable country names
```

---

### IMG-23 · Заставка-фон канала (сц. 27)

**Prompt (B):**
```
Abstract dark background for YouTube channel end card: subtle grid, faint gold horizon line,
deep navy #0d1117, empty center space for logo overlay, cinematic minimal, no text baked in
```

---

## 3. Пары для split-screen (монтаж без gen)

| Левая половина | Правая | Сцена |
|----------------|--------|-------|
| IMG-12 | IMG-13 | 16 |
| IMG-14 | IMG-15 | 17 |
| IMG-01 (цвет) | IMG-02 or desaturated IMG-14 | 01–02 |

---

## 4. Техника генерации

| Параметр | Рекомендация |
|----------|----------------|
| Соотношение | 16:9 |
| Разрешение | ≥1920×1080 или gen 1344×768 + upscale |
| Лица | Избегать крупного плана лиц — меньше артефактов и GDPR-ощущения |
| Текст | **Не в картинке** — только в посте (графика, субтитры) |
| Цветокор | В монтаже: desaturate −15%, shadows в сторону `#0d1117`, чтобы стыковалось с PNG |
| Права | Commercial use, own generation; не копировать узнаваемые рекламы страховых |

**Папка сохранения:** `data/pension/video/graphics/yt-000/images/`  
**Имена:** `IMG-01_beach_ad.png`, …

**Генерация:** `scripts/generate_yt000_images_gemini.py` + `images_config.json`.  
Сейчас в `images/` — **Flux/dev (Fal)**: у `GEMINI_API_KEY` квота 429, Imagen только на paid plan. После пополнения квоты: `--provider gemini --force`.

---

## 5. Приоритет (если бюджет на 8–10 картинок)

Сгенерировать в первую очередь:

1. **IMG-01** — крючок  
2. **IMG-14 + IMG-15** — UK (сердце боли)  
3. **IMG-12 + IMG-13** — контраст Европы  
4. **IMG-05 или IMG-07** — механизм PAYG/баллы  
5. **IMG-18** — Хемингуэй (если не хватает `13_hemingway_quote.png`)  
6. **IMG-21 + IMG-19** — финал «искусный»  
7. **IMG-22** — «ехать некуда»  
8. **IMG-03** — заморозка 2014  

Остальное — сток (завод, протесты) или только графики.

---

## 6. Промпт-шаблон (копипаст)

```
[ОПИСАНИЕ СЦЕНЫ ИЗ ТАБЛИЦЫ ВЫШЕ], cinematic documentary still, 16:9, photorealistic subdued,
desaturated cold grade, no readable text, no logos, no watermark, no celebrity faces,
financial documentary mood
```

**Negative:**
```
cartoon, text, logo, watermark, happy retirement ad, beach commercial cheesy smile,
distorted hands, extra fingers, bright saturated colors, gore
```
