# Снегири · рекламные креативы и визуал (Gemini, сообщение 4)

**Дата:** июль 2026 · ассет: [`static/snegiri/assets/ad-cv-scanner.png`](../static/snegiri/assets/ad-cv-scanner.png) (концепция 2)

---

## 1. Три концепции обложки (Telegram / таргет)

### Концепция 1: «Красный флаг»

| | |
|--|--|
| **Кадр** | Ч/б, нижняя фаза свинга/тяги, скруглённая спина. Красная пунктирная дуга UI + плашка «Угол 42°. Потеря жёсткости». |
| **Эмоция** | Тревога, узнавание ошибки |
| **1 сек** | «Я тоже так делаю, и это опасно» |

**Gemini prompt (1080×1080):**
```
Black and white brutal fitness photo, man at bottom of kettlebell swing, rounded lower back.
Bright red dashed arc overlay on spine, UI label in Russian monospace: "Угол 42°. Потеря жёсткости".
Industrial gym, high contrast, #FF3300 accent only. No cute birds. No wellness stock.
```

### Концепция 2: «Суровый сканер» ✅ (есть референс)

| | |
|--|--|
| **Кадр** | Свинг с CV-скелетом (#FF3300), industrial gym |
| **Эмоция** | Объективность, технологичность |
| **1 сек** | «Телефон видит мои ошибки насквозь» |

Используется на лендинге: `#trust`, `#app-preview`.

**Вариант с телефоном (доработка):**
```
Close-up smartphone on gym floor, screen shows legs and kettlebell with red pose skeleton,
bottom bar text: "Разбор завершён. Оценка: 3/10". Black and white except red UI. Brutal industrial.
```

### Концепция 3: «Фундамент»

| | |
|--|--|
| **Кадр** | Bird-dog McGill, level/green stiffness vector on lumbar, kettlebell side with lock arrow |
| **Эмоция** | Контроль, поэтапность |
| **1 sec** | «Сначала кор, потом железо» |

---

## 2. Пять текстов на баннер (боль)

1. **Ноет спина после офиса?** Гиря добьёт её. Если будешь делать махи вслепую.
2. **Тренируешься по YouTube?** Видеоблогер не остановит тебя, когда у тебя провалится поясница.
3. **Страшно брать вес дома?** И правильно. Сначала сдай ИИ-экзамен на жёсткость кора.
4. **Абонемент в зал не защитит от травмы.** Если рядом нет тренера, ты предоставлен своим ошибкам.
5. **Уверен, что держишь спину ровно?** Алгоритм с тобой не согласится. Проверь бесплатно.

**UTM:** `?utm_source=telegram&utm_medium=cpc&utm_campaign=banner_{1-5}`

---

## 3. App icon brief

**Проблема:** милый снегирь на гире убивает доверие к CV-продукту.

| Вариант | Описание | Файл |
|---------|----------|------|
| **A. Кибер-птица** | Low-poly силуэт, чёрная гиря, красная грудка #FF3300, без «глаз» | TBD PNG 1024 |
| **B. Векторная гиря** ✅ черновик SVG | Чёрный фон, гиря + красная векторная линия с узлами | [`logo-icon-vector.svg`](../static/snegiri/assets/logo-icon-vector.svg) |

**Следующий шаг:** экспорт B в PNG 1024×1024 → заменить `logo-channel-1024.png` в `manifest.json`.

**Gemini prompt (icon B):**
```
App icon 1024x1024, pure black background. Minimal kettlebell silhouette white outline,
pierced by neon red #FF3300 dashed vector line with 3 joint nodes. No text, no bird, no gradients.
Industrial brutal, Apple-style simplicity.
```

---

## 4. Trust block (без лиц экспертов)

Внедрено в [`index.html`](../static/snegiri/index.html) `#trust`:

| Блок | Визуал |
|------|--------|
| Основано на науке | SVG позвоночник + гиря |
| Холодная математика | `ad-cv-scanner.png` |
| Обучено на эталонах | Сетка 6 размытых превью |

После договоров E-tier — добавить цитаты тренеров **под** этими блоками, не вместо.

---

## 5. Figma / Telegram specs

| Формат | Размер | Концепция |
|--------|--------|-----------|
| Telegram post | 1080×1080 | 1, 2 или 3 |
| VK/MyTarget | 1080×607 | 2 (scanner) |
| Stories | 1080×1920 | 1 (red flag) + CTA |

**CTA на креативе:** «Проверь бесплатно» → `app.html`
