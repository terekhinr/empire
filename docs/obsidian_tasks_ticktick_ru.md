# Задачи вместо TickTick (Obsidian + Яндекс.Диск)

VPS **не синхронизирует** `Life/tasks/` — только вы на ПК и телефоне через Яндекс.Диск.

---

## ПК и телефон (один vault)

Путь в vault:

```text
Life/tasks/
  dashboard.md   ← панель (плагин Tasks)
  inbox.md       ← новые задачи
  _import/       ← CSV из TickTick
  README.md
```

### Плагин Obsidian

**Settings → Community plugins → Tasks** → включить.

Горячая закладка: `Life/tasks/dashboard.md`.

### Формат задачи

```markdown
- [ ] Текст 📅 2026-06-15
- [ ] С приоритетом ⏫ 📅 2026-06-16 #работа
- [ ] Повтор 🔁 every week 📅 2026-06-20
```

---

## Android: напоминания (Tasks.org)

Obsidian на телефоне **слабо** пинает по времени.

1. Установите **Tasks.org** (Google Play).
2. Задачи **с точным временем** — дублируйте в Tasks.org (или создавайте сразу там).
3. Всё остальное — в Obsidian `Life/tasks/inbox.md`.

Это нормальная схема: **Obsidian = план**, **Tasks.org = будильник**.

---

## Импорт TickTick

1. [ticktick.com](https://ticktick.com) → Аккаунт → резервная копия → CSV.
2. Сохранить в `Life/tasks/_import/ticktick-backup.csv` (Яндекс.Диск).
3. На ПК (если есть `Life/tools/ticktick_csv_to_obsidian.py`):

```powershell
python "F:\YandexDisk\obsidian (2)\Life\tools\ticktick_csv_to_obsidian.py" `
  "...\ticktick-backup.csv" "...\inbox.md"
```

Или вручную перенести активные строки (Status=0) в `inbox.md`.

---

## Не путать с Empire

| Папка | Назначение |
|-------|------------|
| `Empire/*/queue/` | посты в Telegram |
| `Life/tasks/` | личные дела |
