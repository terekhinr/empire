# Урок 1.3 — Менеджер задач (To-Do List)

## Зачем это нужно
Данные в оперативной памяти исчезают при закрытии программы. Файл `.json` — простой способ «положить данные на диск» без настоящей БД. Позже ты заменишь JSON на SQLite/SQLAlchemy, но идея та же: сохранить → загрузить.

## Теория (кратко)
1. Модуль **`json`**: `json.dump(obj, file)` — записать, `json.load(file)` — прочитать.
2. **`with open(...) as f:`** — безопасное открытие файла (закроется само).
3. Список дел удобно хранить как список словарей:
   ```python
   [{"id": 1, "title": "Купить молоко", "done": False}, ...]
   ```

Аналогия: JSON-файл — как блокнот. Открыл → дописал → закрыл. Забыл закрыть — потеряешь запись.

## Внешний тренажёр
- [Поколение Python (Stepik)](https://stepik.org/course/58852/promo) — работа с файлами.
- Документация: [json — JSON encoder and decoder](https://docs.python.org/3/library/json.html)

## Твоя задача (экзамен модуля 1)
В `solution.py` реализуй класс `TodoList`:

```python
class TodoList:
    def __init__(self, filepath: str): ...
    def add(self, title: str) -> dict: ...
    def complete(self, task_id: int) -> bool: ...
    def remove(self, task_id: int) -> bool: ...
    def list_tasks(self) -> list: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
```

### Правила
1. При создании `__init__` запомни путь к файлу. Если файл уже есть — вызови `load()`, иначе начни с пустого списка `self.tasks = []`.
2. `add(title)` — добавь задачу с новым `id` (1, 2, 3… — следующий после максимального существующего, или `1` если список пуст). Поля: `id`, `title`, `done=False`. Верни созданный словарь. После добавления вызови `save()`.
3. `complete(task_id)` — найди задачу, поставь `done=True`, сохрани, верни `True`. Если не найдена — `False`.
4. `remove(task_id)` — удали задачу, сохрани, верни `True`/`False`.
5. `list_tasks()` — верни текущий список (можно копию).
6. `save()` / `load()` — запись и чтение JSON с диска (кодировка `utf-8`).

## Как проверить
```bash
cd empire_practicum
pytest module_1_python/lesson_3_todo_list/test_task.py -v
```
