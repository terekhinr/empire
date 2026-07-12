# Дизайн v3 · кинематографичный стиль (после step-иконок)

Новые картинки шагов — **эталон стиля**: ч/б фото, руки/штатив, телефон с HUD, единственный красный `#FF3300`.

Логотипы уже подключены: `logo-channel-1024.png`, `logo-header.png`, `logo-engraved.png`.

---

## Сейчас (5 минут)

Скопировать 3 PNG из Gemini в `static/snegiri/assets/`:

| Сохранить как | Что на картинке |
|---------------|-----------------|
| `step-01-camera.png` | Штатив + телефон, REC, съёмка свинга |
| `step-02-ai.png` | Руки держат телефон, ANALYZING POSE, красная линия на спине |
| `step-03-plan.png` | Руки + PERSONAL WEEKLY PLAN, красный день |

```bash
cd /root/projects/empire
./scripts/snegiri_compress_assets.sh
```

Ctrl+F5 на лендинге. Блок «Три шага» подхватит PNG + WebP.

**Бонус:** те же 3 файла можно продублировать для блока «Как выглядит разбор»:

```bash
cp static/snegiri/assets/step-01-camera.png static/snegiri/assets/app-record.png
cp static/snegiri/assets/step-02-ai.png static/snegiri/assets/app-analyze.png
cp static/snegiri/assets/step-03-plan.png static/snegiri/assets/app-result.png
./scripts/snegiri_compress_assets.sh
```

---

## Волна 2 — единый визуал лендинга

Старые hero / tracks / trainer — другой стиль. Перегенерировать **в том же чате**, прикрепив **step-02-ai.png** как референс.

### Мастер-промпт (новый чат)

**Прикрепить:** `step-02-ai.png`, `logo-final-square.png`

```
Ты — арт-директор snegirinegiri.ru. Генерируй изображения.

СТИЛЬ (по референсам):
- Cinematic B&W photography, industrial gym / workshop
- Smartphone with brutalist HUD UI in frame
- ONLY color: #FF3300 (REC dot, CV spine line, calendar highlight)
- Hands, concrete, metal, chiaroscuro — NOT wellness stock

Работай ПО ОДНОМУ файлу:
1) EN prompt 2–3 предложения
2) Сразу сгенерируй — не жди ok
3) Имя файла + размер
4) «Следующий?»

Порядок:
1. hero-mockup-screen.png — 390×844, экран телефона: свинг + красная линия на спине + HUD
2. track-01-spine.png — 800×600, боковая планка, тот же свет/зерно
3. track-02-kettlebell.png — 800×600, свинг гири, тот же стиль
4. trainer-photo.png — 1200×1600, тренер со спины с гирей
5. og-image.png — 1200×630, чёрный фон + гравировка гири + белый текст

Начни с hero. Не всё сразу.
```

---

## Волна 3 — экраны приложения (mockup.html)

Сейчас mockup — CSS-кнопки без картинок. Цель: **9:16 экраны** в стиле step-иконок для вставки в макет.

| Файл | Экран mockup |
|------|----------------|
| `app-splash.png` | Splash (лого + «Школа Штерна») |
| `app-home.png` | Главная, треки S/K |
| `app-record.png` | Запись (уже есть из step-01) |
| `app-analyze.png` | Анализ (step-02) |
| `app-result.png` | План/результат (step-03) |
| `app-subscribe.png` | Тарифы в UI |

Промпт-шаблон для любого экрана:

```
Сгенерируй изображение 390×844. Экран fitness-приложения «Снегири не гири».
Стиль как прикреплённый step-02-ai.png: руки держат телефон ИЛИ чистый UI на чёрном.
B&W + #FF3300 только для акцента. Brutalist HUD, IBM Plex vibe.
Без watermark. Имя: app-[NAME].png
```

После генерации — Cursor: **«вставь app-скрины в mockup»**.

---

## Приоритет

| # | Задача | Кто |
|---|--------|-----|
| 1 | Залить step-01…03 + compress | Ты |
| 2 | Дублировать в app-record/analyze/result | Ты или Cursor |
| 3 | Hero + tracks в новом стиле | Gemini волна 2 |
| 4 | Mockup с реальными скринами | Cursor после волны 3 |
| 5 | DNS snegirinegiri.ru | Ты (`docs/snegiri_deploy_vps.md`) |
