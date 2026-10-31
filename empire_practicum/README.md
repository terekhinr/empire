# Empire Practicum

Локальная образовательная платформа: теория → практика в `solution.py` → автопроверка `pytest` → прогресс в `dashboard.py`.

Цель программы: стек **B2B Lead Bot** (Python → Aiogram 3 → БД → Docker).

## Быстрый старт

```bash
cd empire_practicum
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python dashboard.py
```

## Как учиться

1. Открой `task.md` следующего урока (смотри дашборд).
2. Пройди внешний ресурс (Stepik / Mastergroosha).
3. Напиши код в `solution.py` (ментор Cursor **не** пишет решение за тебя — см. `.cursorrules`).
4. Проверь:
   ```bash
   pytest module_1_python/lesson_1_calculator/test_task.py -v
   ```
5. Когда тесты зелёные — напиши ментору: он обновит `progress.json`.

## Структура

| Модуль | Уроки |
|--------|--------|
| `module_1_python` | Калькулятор → Анализатор текста → To-Do |
| `module_2_async_bots` | Эхо-бот → Клавиатуры → FSM анкета |

Модули 3–4 (SQLAlchemy, Docker, выпускной бот) — следующий этап платформы.

## Важно

- Не коммить токены Telegram и `.env`.
- `solution.py` — твоя зона. Пустые `pass` / `TODO` — нормально до решения.
