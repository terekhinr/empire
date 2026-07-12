# Handoff Gemini 1b · snegirinegiri.ru

Полный ответ Gemini (июль 2026). Внедрено в `static/snegiri/index.html` v0.2.

**Сводная таблица ассетов** — см. конец документа.

---

## Статус внедрения в код

| Файл | Статус |
|------|--------|
| `logo.svg`, иконки шагов, lock, medical, tg, vk, cv-badge | ✅ SVG в `assets/` |
| `og-image.svg` | ✅ (экспорт в PNG для TG — по желанию) |
| `track-*.svg`, `trainer-photo.svg` | ✅ placeholder до MJ |
| `hero-mockup-screen.webp` | ⬜ Midjourney |
| `hero-bg.webp` | ⬜ опционально |
| `track-01-spine.webp`, `track-02-kettlebell.webp` | ⬜ Midjourney |
| `trainer-photo.webp` | ⬜ Midjourney / договор |
| `app-record.webp`, `app-analyze.webp`, `app-result.webp` | ⬜ Figma + фото |
| `favicon.ico`, `logo-og.png` | ⬜ экспорт из Figma |

---

## ЭЛЕМЕНТ 0 — Design system

1. **Назначение:** Единый источник правды для вёрстки и дизайна.
2. **Сетка:** 4 col mobile (margin/gutter 16px), 12 col desktop (max 1120px, gutter 24px).
3. **Файлы:** `assets/icons-sprite.svg` (опционально).
4. **Figma:** Local Variables, Typography, Components (Button/Primary, Ghost, Accordion, Badge).
5. **CSS:** radius 0 везде кроме телефона (24px). Focus `outline: 2px #FF3300`. Hover кнопок — инверсия / #F2F2F2.

---

## ЭЛЕМЕНТ 1 — Логотип

- `logo.svg`, `favicon.ico`, `logo-og.png`
- СНЕГИРИ / НЕ ГИРИ, uppercase, tracking -2%, маркер угла #FF3300

---

## ЭЛЕМЕНТ 2 — Hero

- `hero-bg.webp` (1920×1080), `hero-mockup-screen.webp` (390×844)
- Phone: border 4px #333, radius 24px only here
- MJ EN: kettlebell swing UI overlay, red spine line #FF3300

---

## ЭЛЕМЕНТ 3 — Иконки шагов

- `step-01-camera.svg`, `step-02-ai.svg`, `step-03-plan.svg` (128×128, stroke 2px)

---

## ЭЛЕМЕНТ 4 — Треки

- `track-01-spine.webp`, `track-02-kettlebell.webp`, `icon-lock.svg`
- Progress bar 50% white
- Locked card: opacity 50%, pointer-events none

---

## ЭЛЕМЕНТ 5 — Trust

- `trainer-photo.webp` (600×800), `cv-badge.svg`
- grayscale + contrast 1.2

---

## ЭЛЕМЕНТ 6 — Тарифы

- Кодом. Card 3 (3990): border 2px white, badge −33%

---

## ЭЛЕМЕНТ 7 — FAQ

- `icon-medical.svg` у вопроса про грыжу
- Плюс/минус моноширинный, линии #333

---

## ЭЛЕМЕНТ 8 — Footer

- `icon-tg.svg`, `icon-vk.svg`
- Дисклеймер uppercase mono 10–12px #666

---

## ЭЛЕМЕНТ 9 — OG

- `og-image.png` 1200×630, safe zone 800×400

---

## ЭЛЕМЕНТ 10 — App UI

- `app-record.webp`, `app-analyze.webp`, `app-result.webp` (390×844)

---

## Сводная таблица ассетов

| Имя файла | Размер | Блок |
| --- | --- | --- |
| `logo.svg` | SVG | Хедер, футер |
| `favicon.ico` | 32×32 | Head |
| `logo-og.png` / `og-image.svg` | 1200×630 | OG |
| `hero-bg.webp` | 1920×1080 | Hero фон |
| `hero-mockup-screen.webp` | 390×844 | Hero phone |
| `step-01-camera.svg` … `step-03-plan.svg` | 128×128 | Шаги |
| `track-01-spine.webp` | 400×300 | Треки |
| `track-02-kettlebell.webp` | 400×300 | Треки |
| `icon-lock.svg` | 24×24 | Треки |
| `trainer-photo.webp` | 600×800 | Trust |
| `cv-badge.svg` | ~140×32 | Trust |
| `icon-medical.svg` | 24×24 | FAQ |
| `icon-tg.svg`, `icon-vk.svg` | 24×24 | Footer |
| `app-record.webp` … `app-result.webp` | 390×844 | App preview |

---

## Порядок работы

1. Midjourney → webp в `assets/` (имена как в таблице)
2. Figma → доработка иконок / OG PNG
3. Cursor уже подставит по `<picture>` — webp приоритет, svg fallback

## Critical Don'ts

- Цвета: только #000, #FFF, серые, #FF3300
- radius: 0 (кроме телефона)
- Без blur box-shadow
- Без wellness-эстетики
