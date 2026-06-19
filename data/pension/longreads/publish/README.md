# Публикация Дзен / VK · формат «как у Мячина»

## Автопост из Empire (основной путь)

| Куда | Формат в БД `post_drafts.text_content` | Как уходит |
|------|----------------------------------------|------------|
| **Дзен** | HTML + `<img src="https://neverretire.ru/static/longreads/…">` | `dzen_rss` → `media/rss_pension.xml` |
| **VK** | тот же HTML → plain text | `vk_wall` (картинки на стену — v1 только текст) |
| **Telegram** | HTML | бот, parse_mode HTML |

**Око Саурона** → вкладка **«Лонгриды · Дзен/VK»**:
1. Выбрать выпуск 00–04 и площадку (dzen/vk md)
2. Превью: Дзен / VK / RSS / правка HTML
3. **«В очередь модерации»** → **«Модерация постов»** → каналы `tg` + `vk_wall` + `dzen_rss` → Опубликовать

Исходники: `publish/dzen|vk/NN.md` → конвертер `longread_empire.py`.

```bash
python3 tools/build_longread_publish.py   # тексты md
python3 tools/build_longread_preview.py    # PNG + локальный preview/index.html
```

Картинки для RSS: `static/longreads/01|02/*.png` (копируются при превью в дашборде).

## Ручной постинг (запасной)

Копипаст из `.md` + PNG из `graphics/NN/png/` — если Empire недоступен.

## Как устроен текст

1. **Заголовок-вопрос** (первая строка) — в Дзене дублируйте в поле «Заголовок».
2. **Короткие абзацы**, подзаголовки `##`, списки и таблицы — как в «Простой экономике».
3. **Ссылки** — кликабельный текст `[название](url)` или голый URL после цифры.
4. **Иллюстрации** — строки `*[Вставьте картинку: …]*` + таблицы (можно снять скрин таблицы, если редактор не вставляет markdown).
5. В конце — ссылка на книгу с UTM и дисклеймер.

## Дзен vs VK

| | Дзен | VK |
|---|------|-----|
| Файл | `dzen/00..04.md` | `vk/00..04.md` |
| Заголовок | `# Вопрос?` в файле | первая строка = заголовок поста |
| Лид | сразу после заголовка | + короткий лид одной строкой |
| UTM | `utm_source=dzen` | `utm_source=vk` |

## Пересборка

```bash
python3 tools/build_longread_publish.py
```

Исходники текстов — в `tools/build_longread_publish.py` (функции `article_00` … `article_04`).

Базовые черновики (длинные): `../00_pilot_neverretire.md` … `../04_inflaciya_gosplan.md`.

См. `docs/pension_reference_myachin.md` · `docs/pension_content_calendar_2026.md`
