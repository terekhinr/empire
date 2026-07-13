# Workflow · одно упражнение · Gemini

**Принцип:** не пакет, а **1 slug за раз**. Качество > скорость.

---

## День 1 · Подготовка (без картинки)

1. Открыть [`snegiri_comic_errors_catalog.md`](snegiri_comic_errors_catalog.md) — дописать/утвердить slug.
2. `python3 scripts/build_comic_briefs.py && ./scripts/sync_snegiri_comic_briefs.sh`
3. Сгенерировать промпт:
   ```bash
   python3 scripts/render_comic_prompt.py --master   # новая сессия Gemini
   python3 scripts/render_comic_prompt.py --slug rack_hold --performer m > /tmp/rack_hold_m.txt
   ```
4. Вручную вставить в конец промпта блок **техники** из catalog (пока скрипт не склеивает сам).

**Вложения Gemini:** `hero-poster.png` + (опц.) скрин YouTube школы **без** watermark чужого бренда.

---

## День 2 · Мужчина (M)

1. Отправить мастер-промпт + промпт M.
2. Сохранить: `assets/comics/_draft/rack_hold_m.png`
3. **QA** ([`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md) + catalog):
   - RU подписи
   - 1 гиря / правильный хват
   - локти по школе
   - нет штанги
   - industrial gym фон
4. Провал → правка catalog/brief → **новый** промпт (не amend в Gemini).

---

## День 3 · Женщина (F)

1. ```bash
   python3 scripts/render_comic_prompt.py --slug rack_hold --performer f > /tmp/rack_hold_f.txt
   ```
2. **Обязательно приложить** утверждённый `rack_hold_m.png`.
3. QA: та же хореография, та же гиря, правая рука если одноручное.

---

## День 4 · Прод

```bash
cwebp -q 85 rack_hold_m.png -o static/snegiri/assets/comics/rack_hold_m.webp
python3 scripts/slice_comic_strip.py --slug rack_hold
./scripts/sync_snegiri_comic_phases.sh
```

В brief: `"status": "ok"`, `"qa_notes": "..."`.

---

## Cursor (A/B только)

Тот же промпт из `render_comic_prompt.py` — сравнить с Gemini на 1–2 slug. **Не** вести каталог через Cursor, если Gemini стабильно лучше.

---

## Рекомендуемая очередь (первые 8)

1. `rack_hold` — треугольник локтей (Алферова)
2. `jerk` — локоть на подвздошную
3. `clean` — мягкий заброс
4. `swing` — маятник
5. `curl_up` — McGill
6. `side_plank`
7. `snatch` — просов кисти
8. `hand_switch` — мёртвая точка

По ~2 дня на упражнение (M+F) ≈ **16 дней** на ядро.
