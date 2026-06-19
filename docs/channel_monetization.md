# Монетизация по каналам (модель Empire)

| Канал / проект | Механика | Бот / инструмент | Статус |
|----------------|----------|------------------|--------|
| **Ленин** | Донаты (Stars) | `empire_donate_bot.py` | ✅ код |
| **Штерн** | Продажа инфопродукта (tripwire → курс) | `empire_stern_bot.py` + YooKassa | ✅ lead, 🔒 оплата |
| **Сад и огород** | Продажа инфопродукта | `empire_garden_bot.py` | ✅ каркас, 🔒 оплата |
| **Где пар** | Реклама **gdepar.ru** в автопостах + Метрика UTM | `gdepar_content` / `promo_map` | ✅ промо-посты |
| **Где пар (сайт)** | Опционально позже: сбор на хостинг карты | отдельный слот или тот же донат-бот с кампанией `gdepar_site` | ⬜ не включено |

## Ленин — только донаты

- Бот: `DONATE_BOT_TOKEN`, username в `EMPIRE_DONATE_BOT_USERNAME`
- Ссылка: `https://t.me/<бот>?start=donate_lenin`
- Док: `docs/donate_bot_setup.md`

## Штерн и Garden — продажники

- **Не** использовать донат-бот.
- Общая БД: `sales.db` (`products`, `orders`, `entitlements`).
- Штерн: `data/stern_products.json`, бот `STERN_BOT_TOKEN`.
- Garden: `GARDEN_BOT_TOKEN`, каталог `data/garden_products.json`, ТЗ `docs/garden_infoproduct_tz.md`, setup `docs/garden_bot_setup.md`.

## Garden — рост и продажи (без опоры на TG в РФ)

- Привлечение: **ВК, Дзен, MAX** — см. `docs/garden_growth_rf_no_vpn.md`
- Продажи PDF: VK + ЮKassa (приоритет); TG-бот — опционально для аудитории с VPN

## Где пар — трафик на сайт

- Еженедельный пост понедельник 10:00 → `type: promo_map`, UTM на gdepar.ru.
- Аналитика: Метрика + `tg_promo_map_draft` в `analytics.db`.
- Сбор на поддержку **сайта** (не канала) — по решению позже; не смешивать с Лениным без отдельной кампании.
