# Спецификация мультиков-эталонов v1

> **Superseded:** канон в [`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md). Этот файл — история решений. A/B локации: **industrial_gym vs home_room** (не garage).

**Дата:** июль 2026  
**Статус:** **канон зафиксирован** · генерация каталога после A/B  
**Связано:** [`snegiri_comic_ab_tests.md`](snegiri_comic_ab_tests.md) · `snegiri_kb/comic_briefs_data.json` · `scripts/render_comic_prompt.py`

---

## 1. Проблема (почему остановились)

| Сбой | Причина |
|------|---------|
| Зал / штанга | промпт `industrial gym` + слабый brief |
| RU / EN | подписи не из одного источника |
| 1 vs 2 гири | не зафиксировано в brief |
| M ≠ F | F без референса M |

---

## 2. Что мы хотим (продукт)

| Принцип | Решение |
|---------|---------|
| Где тренируется пользователь | **Дом** (комната или гараж), не зал |
| Базовый инвентарь | **1× гиря 16 кг** на весь стартовый курс |
| Исключения веса | K4 halo **12 кг** (всё ещё одна гиря) · S4 резина |
| Продвинутый tier | **2×16 кг** — отдельные эталоны `*_2kb_*.webp`, после базового курса |
| Подписи на ленте | **русский** из `labels_ru` |
| M и F | **одна хореография**; F только после QA M + с референсом |
| Одноручные | **правая** рука у M и F |
| CV-ракурс | `camera` из brief = `program_data` |

---

## 3. Источник правды

**Файл:** `snegiri_kb/comic_briefs_data.json` (25 упражнений)

Сборка: `python3 scripts/build_comic_briefs.py`  
Синк в app: `./scripts/sync_snegiri_comic_briefs.sh`

Промпт: `python3 scripts/render_comic_prompt.py --slug {slug} --performer m|f`

`comic_phases_data.json` — термины в UI (уже RU, совпадают с `labels_ru`).

---

## 4. Локация (default + A/B)

| Трек | Default | A/B |
|------|---------|-----|
| S | `home_room` + коврик | vs `home_garage` на пилотах |
| K | `home_garage` + бетон | vs `home_room` на пилотах |

**Пилоты:** `curl_up`, `swing`, `halo` × M × 2 локации = **6 картинок**  
Протокол: [`snegiri_comic_ab_tests.md`](snegiri_comic_ab_tests.md)

---

## 5. Пайплайн (единственный правильный)

```
build_comic_briefs.py
    → render_comic_prompt.py --performer m
    → Gemini / Cursor → QA
    → status m_ok
    → render_comic_prompt.py --performer f (+ ref M)
    → QA → status ok
    → slice_comic_strip.py → sync phases
```

**Запрещено:** пакетная генерация F без M · промпты без brief · §5 old «industrial gym».

---

## 6. Текущие ассеты

| Что | Статус |
|-----|--------|
| 50 лент в `assets/comics/` | `needs_regen` в brief |
| `*_v2.png` черновики | не в прод |
| swing/hand_switch v1 | тоже пересмотреть после A/B |

В прод **не** выкатывать каталог как финал до `status: ok`.

---

## 7. Следующие шаги

1. **Ты или я** — прогнать A/B локации (6 img) → записать победителя.
2. **A/B M→F** на `clean` (4 img) → выбрать strip vs panel-by-panel.
3. Обновить `_meta.ab_winners` в briefs.
4. Волна 1: S1–S3, K1–K3, K6 по пайплайну.
5. Остальной каталог.

**Команды пилотов:** [`snegiri_comic_ab_prompts.md`](snegiri_comic_ab_prompts.md)

---

## 8. Tiers гирь (base / advanced)

| Tier | Когда | Эталоны |
|------|-------|---------|
| **base** | Весь стартовый курс | одна 16 кг; `farmer_walk_m.webp` |
| **advanced** | После базы / при 2-й гире | `farmer_walk_2kb_m.webp` (пока только S7) |

Прогнать A/B оборудования в Gemini **и** Cursor — [`snegiri_comic_ab_tests.md`](snegiri_comic_ab_tests.md) §2.

Всё остальное — **зафиксировано**, ждём A/B (локация, M→F, гири).
