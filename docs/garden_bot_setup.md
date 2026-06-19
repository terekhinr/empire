# Бот продаж «Сад и огород»

Инфопродукт: `docs/garden_infoproduct_tz.md`.

## Env

```bash
GARDEN_BOT_TOKEN=...
EMPIRE_GARDEN_BOT_USERNAME=stepanych_garden_bot
```

## Запуск

```bash
sudo cp deploy/empire_garden_bot.service /etc/systemd/system/
sudo systemctl enable --now empire_garden_bot
```

## Ссылка в канале

```
https://t.me/<username>?start=channel_weekly
```

Воскресенье 16:00 — автопост с ссылкой (`type: bot_promo`).

## Команды бота

| Команда | Действие |
|---------|----------|
| `/start` | Дисклеймер → lead → каталог |
| `/catalog` | Каталог PDF |
| `/waitlist` | Лист ожидания до YooKassa |

## Дальше

1. PDF в `data/garden_deliverables/pdf/` (пересборка: `./venv/bin/python scripts/build_garden_pdfs.py all`).  
2. Превью для ВК: `garden_tripwire_preview_3_errors.pdf` → `build_garden_pdfs.py preview`.  
3. Оформление ВК и ручные продажи: `docs/garden_vk_sales_funnel_ru.md`, тексты `data/garden_vk_copy.json`.  
4. ЮKassa + VPS: `docs/infoproduct_yookassa_npd_setup_ru.md`.  
5. Включить `payments_enabled` + webhook `empire_sales` (когда API оплаты в боте готов).
