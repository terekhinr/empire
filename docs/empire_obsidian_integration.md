# Obsidian ↔ Empire: как связать «стол» текстов с ботом

**Практический гайд (Obsidian → Telegram, все каналы):** `docs/obsidian_practical_guide_ru.md`  
**Краткая шпаргалка для vault:** `templates/obsidian_vault_README.md` → скопировать в `Empire/README.md` в Obsidian.

**Цель:** писать запасом в Obsidian (шаблоны, канвас, сценарии), а Empire забирает готовые заметки, оборачивает в HTML/Telegram и ведёт к approve → канал.

---

## 1. Принцип разделения ролей

| Obsidian | Empire |
|----------|--------|
| Мышление, черновики, канвас, ссылки между заметками | Расписание, `PostDraft`, Telegram approve, `finalize_public_post`, каналы |
| Формат: Markdown + YAML frontmatter | Импорт → `data/obsidian_import_queue.json` (сейчас) → позже очередь в БД + тикер |

Канвас и Dataview в Obsidian **не** читает бот напрямую: они остаются вашей «картой работы». В публикацию попадает только то, что лежит в **согласованной папке** и проходит импорт.

---

## 2. Рекомендуемая структура vault

Создайте в vault отдельную ветку под империю (не смешивать с личными дневниками):

```text
Empire/
  README.md                 # правила для себя
  pension/                  # черновики под «На пенсию никогда»
    2026-05-25-rates.md
    queue/
      _template.md
  stern/
  gdepar/
  _canvas/                  # сценарии — только для вас; импорт их не трогает
    pension-pipeline.canvas
```

Импорт сканирует **только** каталог, который вы задаёте переменной окружения (см. ниже), например `…/Empire/pension/queue/`.

---

## 3. Формат заметки (frontmatter + тело)

Минимальный контракт для скрипта `scripts/import_obsidian_queue.py`:

```yaml
---
id: rates-may-2026          # уникальный ключ; иначе — из имени файла
persona: pension            # pension | gdepar | stern | lenin | garden
title: "Ставки и депозиты" # заголовок для обёртки
scheduled: "2026-05-25 09:00"  # опционально; ISO или локальное время (см. скрипт)
status: draft               # draft | ready | imported (после импорта можно менять вручную)
---

Текст поста как вы его написали. Абзацы, списки — обычный Markdown.

Второй абзац…
```

- **Сырой текст без frontmatter** — тоже ок: тогда `title` = имя файла, `persona` = из пути или дефолт `pension`.
- **Теги внизу** можно не писать в Obsidian: Empire при сборке поста может вызвать `finalize_public_post` и добавить строку хештегов для pension.

**Форматирование в Telegram** (модуль `telegram_md.py`, вызывается из `fix_html_safety` при постинге):

| В Obsidian | В Telegram |
|------------|------------|
| `[текст](https://…)` | кликабельная ссылка |
| `https://…` в строке | кликабельная ссылка |
| `> цитата` (несколько строк `>`) | `<blockquote>` |
| `[[https://…\|подпись]]` | ссылка |
| `[[заметка]]` / `[[заметка\|подпись]]` | текст (без vault на сервере) |
| `**жирный**`, `*курсив*`, `***оба***` | `<b>`, `<i>` |

Горизонтальная линия `---` в теле поста убирается (остаётся пустая строка). Заголовок поста — из поля `title` в YAML, в тексте дублировать `#` не обязательно.

---

## 4. Как физически «соединить» репозиторий и vault

Выберите один вариант:

1. **Vault внутри `empire`** (подпапка `vault/` в `.gitignore`) — один клон, проще CI.
2. **Git submodule** — `empire/vault-obsidian` → отдельный приватный репо с vault.
3. **Симлинк** — `data/obsidian_incoming` → `~/ObsidianVault/Empire/pension/queue`.
4. **Только копирование** — раз в день rsync/scp на сервер в `OBSIDIAN_EMPIRE_INCOMING`.

Импорт **не требует** установленного Obsidian на сервере — только файлы `.md`.

---

## 5. Импорт в Empire (сейчас)

```bash
export OBSIDIAN_EMPIRE_INCOMING=/path/to/Obsidian/Empire/pension/queue
cd /root/projects/empire
./venv/bin/python scripts/import_obsidian_queue.py
```

Результат: `data/obsidian_import_queue.json` (или путь из `OBSIDIAN_IMPORT_QUEUE_OUT` для тестов/CI).

**Важно:** каждый запуск скрипта **перезаписывает** JSON целиком по всем `.md` в входной папке (снимок `queue/`). Подробнее: `docs/obsidian_practical_guide_ru.md` §D.

---

## 6. Что делать с канвасом

- Канвас: блоки «идея → тезисы → готовый пост» — оставляйте в `_canvas/`.
- **Один финальный `.md`** на пост в `queue/` — это единственный артефакт для импорта.
- Так вы не пытаетесь парсить `.canvas` JSON в Python без необходимости.

---

## 7. Дорожная карта (кратко)

| Этап | Состояние |
|------|-----------|
| Импорт `.md` → JSON | ✅ `scripts/import_obsidian_queue.py` |
| Тикер: `scheduled` → черновик + `notify_admin` | 🔜 отдельная задача |
| Обёртка `📌 {title}` + `finalize_public_post` | 🔜 общая функция + кнопка approve как сейчас |
| Опционально: push из Obsidian Git → CI → импорт на VPS | по желанию |

---

## 8. Шаблон заметки в Obsidian

Скопируйте в свои Templates: `templates/obsidian_empire_post.md` (в репозитории Empire).
