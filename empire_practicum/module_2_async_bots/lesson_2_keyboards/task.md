# Урок 2.2 — Клавиатуры (Inline и Reply)

## Зачем это нужно
Кнопки превращают бота из «текстового чата» в удобный интерфейс: клиент выбирает услугу одним тапом. В B2B Lead Bot так выбирают продукт и подтверждают заявку.

## Теория (кратко)
1. **Reply-клавиатура** — кнопки вместо обычной клавиатуры телефона. Текст кнопки уходит как обычное сообщение.
2. **Inline-клавиатура** — кнопки под сообщением. Дают `callback_data` — короткий код, который ловит другой хендлер.
3. В Aiogram 3:
   - `ReplyKeyboardMarkup` + `KeyboardButton`
   - `InlineKeyboardMarkup` + `InlineKeyboardButton`

Аналогия: Reply — как меню ресторана на столе (всегда под рукой). Inline — как кнопки на чеке «оставить чаевые / нет».

## Внешние ресурсы
- [Aiogram 3 Guide — Клавиатуры](https://mastergroosha.github.io/aiogram-3-guide/buttons/)
- Sudotach — видео про Inline / Reply кнопки

## Твоя задача
Снова чистая логика без Telegram API — тесты проверяют структуры данных.

### 1. `build_reply_menu(options: list[str]) -> list[list[str]]`
Собери Reply-меню: каждая опция — отдельный ряд из одной кнопки.
```python
build_reply_menu(["Услуга A", "Услуга B"])
# → [["Услуга A"], ["Услуга B"]]
```
Пустой список → `[]`.

### 2. `build_inline_services(services: dict[str, str]) -> list[dict]`
`services` — словарь `{callback_data: текст_кнопки}`.
Верни список словарей вида:
```python
{"text": "Баня", "callback_data": "service_banya"}
```
Порядок — как в `services.items()`.

### 3. `parse_callback(data: str) -> dict`
Разбери `callback_data` формата `"service:<slug>"` или `"confirm:<yes|no>"`.
- `"service:banya"` → `{"type": "service", "value": "banya"}`
- `"confirm:yes"` → `{"type": "confirm", "value": "yes"}`
- Неизвестный формат → `{"type": "unknown", "value": data}`

## Как проверить
```bash
cd empire_practicum
pytest module_2_async_bots/lesson_2_keyboards/test_task.py -v
```
