# Донат-бот канала «Ленин»

Один бот, одна кампания: **поддержка TG-канала Ленин** через Telegram Stars.

Другие каналы:
- **Где пар** — промо gdepar.ru в автопостах (не этот бот).
- **Сад и огород** / **Штерн** — боты **продаж** инфопродукта (`empire_garden_bot`, `empire_stern_bot`).

См. сводку: `docs/channel_monetization.md`.

## 1. BotFather

1. Создать бота (например `@empire_lenin_donate_bot`).
2. Включить **Telegram Stars** (Payments).

```bash
DONATE_BOT_TOKEN=...
EMPIRE_DONATE_BOT_USERNAME=empire_lenin_donate_bot
```

## 2. Ссылка для канала

```
https://t.me/<username>?start=donate_lenin
```

С меткой поста: `?start=donate_lenin_weeklypost`

Воскресные автопосты подставляют ссылку сами (`lenin_content.py`).

## 3. Запуск

```bash
sudo cp deploy/empire_donate_bot.service /etc/systemd/system/
sudo systemctl enable --now empire_donate_bot
```

## 4. Статистика

- `/stats` — только для `ADMIN_ID`
- `analytics.db`: `donate_bot_start`, `donation_paid`
- SQL: `SELECT * FROM donations WHERE campaign_code='lenin'`

## 5. Старые ссылки donate_gdepar / donate_garden

Бот покажет подсказку («идите на gdepar.ru / ждите бот продаж») и меню доната **Ленина** — чтобы не ломать переходы по ошибке.
