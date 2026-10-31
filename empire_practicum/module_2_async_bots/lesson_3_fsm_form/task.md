# Урок 2.3 — FSM Анкета (Имя → Телефон → Услуга)

## Зачем это нужно
FSM (Finite State Machine) — машина состояний: бот помнит, на каком шаге диалога находится пользователь. Без FSM бот «глухой» — не отличит имя от телефона. В B2B Lead Bot анкета — ядро продукта.

## Теория (кратко)
1. Состояния — как комнаты: `waiting_name` → `waiting_phone` → `waiting_service` → `done`.
2. В Aiogram 3: `StatesGroup` + `State`, хранилище `MemoryStorage` (пока в оперативке).
3. На каждом шаге: проверить ввод → сохранить в `state.update_data` → перейти дальше.

Аналогия: анкета в поликлинике. Сначала ФИО, потом телефон, потом «к какому врачу». Нельзя сразу писать «к хирургу», пока не назвали имя — регистратор тебя вернёт на шаг назад.

## Внешние ресурсы
- [Aiogram 3 Guide — FSM](https://mastergroosha.github.io/aiogram-3-guide/fsm/)
- Sudotach — FSM / анкета

## Твоя задача
Реализуй мини-FSM **без aiogram** (чистый Python) — так проще тестировать. Позже перенесёшь идеи в `StatesGroup`.

### Состояния
```text
idle → name → phone → service → done
```

### API

```python
class LeadFormFSM:
    def __init__(self): ...
    def start(self) -> str: ...          # → "name", сброс данных
    def current_state(self) -> str: ...
    def process(self, text: str) -> dict: ...
    def get_data(self) -> dict: ...
```

### Правила `process(text)`
Верни словарь вида:
```python
{"ok": True/False, "message": str, "state": str}
```

1. Состояние `name`: текст не пустой → сохранить `name`, перейти в `phone`, сообщение `"Как тебя зовут?"` уже было при start; после успешного имени: `"Принято. Теперь телефон:"`.
2. Состояние `phone`: текст должен содержать **хотя бы 10 цифр** (можно с `+`, пробелами, `-`). Успех → `service`, сообщение `"Какая услуга нужна?"`. Провал → остаться в `phone`, `"Телефон слишком короткий"`.
3. Состояние `service`: непустой текст → сохранить, перейти в `done`, сообщение с итогом, например:
   `"Готово! Имя: Иван, телефон: +7..., услуга: Баня"`.
4. Если вызвали `process` из `idle` или `done` — `{"ok": False, "message": "Сначала /start", "state": ...}`.

### `start()`
- Очистить данные, state = `"name"`.
- Вернуть строку-приглашение: `"Как тебя зовут?"`.

### `get_data()`
- Вернуть `{"name": ..., "phone": ..., "service": ...}` (ключей может не быть, пока не заполнены).

## Как проверить
```bash
cd empire_practicum
pytest module_2_async_bots/lesson_3_fsm_form/test_task.py -v
```
