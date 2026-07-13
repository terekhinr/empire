# A/B пилоты · готовые промпты (копировать)

Сгенерировано из `comic_briefs_data.json`. Перед копированием:

```bash
cd /root/projects/empire
python3 scripts/build_comic_briefs.py   # если briefs менялись
```

Мастер-промпт Gemini (первое сообщение + `hero-poster.png`):

```bash
python3 scripts/render_comic_prompt.py --master
```

---

## Локация · curl_up · M · home_room

```bash
python3 scripts/render_comic_prompt.py --slug curl_up --performer m --ab-location home_room
```

## Локация · curl_up · M · home_garage

```bash
python3 scripts/render_comic_prompt.py --slug curl_up --performer m --ab-location home_garage
```

## Локация · swing · M · home_garage

```bash
python3 scripts/render_comic_prompt.py --slug swing --performer m --ab-location home_garage
```

## Локация · swing · M · home_room

```bash
python3 scripts/render_comic_prompt.py --slug swing --performer m --ab-location home_room
```

## Локация · halo · M · home_garage

```bash
python3 scripts/render_comic_prompt.py --slug halo --performer m --ab-location home_garage
```

## Локация · halo · M · home_room

```bash
python3 scripts/render_comic_prompt.py --slug halo --performer m --ab-location home_room
```

---

## M→F · clean · M (эталон)

```bash
python3 scripts/render_comic_prompt.py --slug clean --performer m
```

## M→F · clean · F (после QA M, приложить clean_m)

```bash
python3 scripts/render_comic_prompt.py --slug clean --performer f
```

---

## Оборудование · farmer_walk · base (1 гиря) · M

```bash
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier base
```

## Оборудование · farmer_walk · advanced (2 гири) · M

```bash
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier advanced
```

## Оборудование · suitcase_carry · base · M (сравнить с farmer)

```bash
python3 scripts/render_comic_prompt.py --slug suitcase_carry --performer m --tier base
```

---

Полный текст промпта — stdout команды. Для Cursor JSON:

```bash
python3 scripts/render_comic_prompt.py --slug clean --performer m --json
```
