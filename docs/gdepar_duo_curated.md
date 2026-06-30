# Импорт постов «Дуэт» (Михалыч ↔ Кириллыч)

Формат для `data/gdepar_duo_curated_import_raw.md`:

```markdown
---
id: duo_unique_id
pool: practice
tag: психология
headline: Заголовок поста
hashtags: #баня #гдепар #психология
image_file: media/gdepar/duo/optional.jpg
---

🔥 **Заголовок** (можно дублировать)

**Михалыч:** Текст реплики.

**Кириллыч:** Текст реплики.

**Михалыч:** Ещё реплика.
```

**pool:** `practice` (11:00), `evening` (21:00), `banya_week` (пятница, со ссылкой на карточку).

**Правила (как у «Классической бани»):**
- Никаких выдуманных процентов, градусов и «исследований».
- Кириллыч — быт, техника, отзывы с карты; без «датчиков 85°C».
- Михалыч — традиция, этикет, без морали «ты обязан».
- Ссылка на gdepar.ru — нативно, 0–1 на пост.

Сборка:

```bash
./venv/bin/python scripts/parse_gdepar_duo_import.py
```

Проверка очереди:

```bash
./venv/bin/python -c "import gdepar_duo_curated as d; print(d.pick_entry(pool='practice'))"
```
