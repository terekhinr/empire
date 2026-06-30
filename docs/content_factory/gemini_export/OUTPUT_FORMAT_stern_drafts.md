# Формат черновиков Stern → Empire

После QUALITY собери батч в markdown.

## Шаблон одного поста

```markdown
---
id: stern_ev_042
slot: 1900
topic_raw: [Психология] Выгорание и дисциплина.
hashtags: #снегири #штерн #психология
image_prompt_en: wooden home gym kettlebell neutral spine soft light photorealistic no face
---

🏛️ <b>Заголовок</b>

Абзац 1…

Абзац 2…

#снегири #штерн #психология
```

## Правила
- slot: `0930` | `1900`
- topic_raw — как в матрице (для scheduler).
- HTML `<b>` в теле.
- Ровно **≤3** хэштега в последней строке.
- image_prompt_en — одна строка EN, без неона.

## Именование файлов от Gemini

`stern_batch_01_drafts.md`, …

Владелец импортирует вручную или через будущий скрипт `parse_stern_import.py`.
