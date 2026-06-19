# Запуск инфопродуктов Garden + Stern — что нужно кроме PDF

Краткий чеклист «площадки, реквизиты, юрлицо». Детали: `docs/garden_infoproduct_tz.md`, `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md` §4.7, `docs/garden_growth_rf_no_vpn.md`.

## Напоминания

- **21.05.2026 ~09:00** — оформить ВК Сад: [`docs/reminders/2026-05-21_09_vk_garden.md`](reminders/2026-05-21_09_vk_garden.md) (будильник на телефоне).

## Полные гайды (пошагово)

| Пункт плана | Документ |
|-------------|----------|
| **П.1** НПД + ЮKassa + VPS | [`docs/infoproduct_yookassa_npd_setup_ru.md`](infoproduct_yookassa_npd_setup_ru.md) |
| **П.3** ВК → tripwire → гайд | [`docs/garden_vk_sales_funnel_ru.md`](garden_vk_sales_funnel_ru.md) + тексты [`data/garden_vk_copy.json`](../data/garden_vk_copy.json) |

---

## 1. Юрлицо и деньги (обязательно для приёма оплаты)

| Что | Зачем | Статус у вас |
|-----|--------|--------------|
| **Самозанятость (НПД)** или ИП | Легальная выручка, лимит НПД ~2,4 млн ₽/год | Проверить в «Мой налог» |
| **ЮKassa** (тариф **для самозанятых**) | Оплата картой + **чеки 54-ФЗ** автоматом | Shop ID + секрет в `.env` |
| **Расчётный счёт / карта для выплат** | Куда ЮKassa выводит; не «любая карта физлица» без привязки к кабинету | В кабинете ЮKassa |
| Webhook | `https://pay.neverretire.ru/webhook/yookassa` → `empire_sales:8002` | Каркас на VPS |
| `payments_enabled: true` | В `data/garden_products.json` / `stern_products.json` | Сейчас **false** |

**Отдельная «карта для рекламы»** не обязательна для продаж — нужна **карта/счёт, привязанные к ЮKassa** для зачисления. Для таргета ВК — отдельный способ оплаты рекламы (карта или кабинет VK Рекламы).

**Telegram Stars** — только донаты (Ленин, Где пар). **Не** для курса «Железная спина» и garden PDF (решение в ТЗ).

---

## 2. Площадки (не только Telegram)

### Сад (Степаныч)

| Площадка | Роль | VPN |
|----------|------|-----|
| **ВК-сообщество** | Главный «дом» аудитории, продажа PDF, обсуждения | нет |
| **Дзен** | Статьи, холодный трафик → ссылка на ВК | нет |
| **MAX** | Короткие анонсы (когда адаптер) | нет |
| **Telegram** | Автопост Empire + бот для тех, у кого VPN | да |

Воронка без VPN: `docs/garden_growth_rf_no_vpn.md` — **продажа приоритетно ВК + ЮKassa**, TG-бот вторичен.

### Штерн

| Площадка | Роль |
|----------|------|
| **Telegram-канал** | Трафик, рубрики, 1 открытый фрагмент урока |
| **TG-бот «Железная спина»** | Онбординг, дисклеймер, оплата, выдача уроков |
| **ВК / Дзен / Shorts** | Посевы → deeplink в бот (`?start=vk_…`) |
| **Отдельный VK-бот** | **Нет в v1** — только ссылка в TG |

---

## 3. Техника на VPS (Empire)

| Компонент | Garden | Stern |
|-----------|--------|-------|
| Бот | `GARDEN_BOT_TOKEN`, `empire_garden_bot` | `STERN_BOT_TOKEN`, `empire_stern_bot` |
| Каталог | `data/garden_products.json` | `data/stern_products.json` |
| PDF | `data/garden_deliverables/pdf/` | Видео + `fallback_url` в `sales.db` |
| Платежи | `empire_sales` + `sales.db` | то же |
| Аналитика | `garden_bot_start`, `garden_order_paid` | `bot_started`, purchase events |

Env-примеры: `.env.example`, `deploy/gdepar.production.env.example` (общие ключи OpenRouter не путать с YooKassa).

---

## 4. Контент-блокеры (до включения оплаты)

### Garden
- [x] Тексты tripwire + гайд 4 недели  
- [x] PDF пересборка (`scripts/build_garden_pdfs.py`)  
- [ ] Сообщество **ВК** создано, закреп, превью 3 ошибок  
- [ ] Тестовая оплата 290 ₽ (после ЮKassa)  

### Stern
- [ ] **3 урока tripwire сняты и приняты** (блокер в ТЗ)  
- [x] Дисклеймер в боте  
- [ ] `lessons` в БД + `fallback_url` на видео  
- [ ] 1 урок в открытом посте канала  
- [ ] Тестовая оплата 390 ₽  

---

## 5. Что НЕ нужно на старте

- Отдельный ИП-магазин на Tilda (опционально позже для рекламы вне TG).  
- Stripe / зарубежные карты (MVP — карты РФ через ЮKassa).  
- Отдельная карта «для инфопродукта» — достаточно кабинета ЮKassa + НПД.  
- Telegram Premium / Stars для продажи курсов.

---

## 6. Порядок включения (рекомендация)

1. НПД + кабинет ЮKassa + webhook на VPS.  
2. **Stern:** 3 урока → тест 390 ₽ → курс 4900 ₽.  
3. **Garden:** ВК + tripwire 290 ₽ → upsell 1290 ₽.  
4. Метрика/UTM: `source_id` в ссылках бота (`?start=channel_weekly`, `vk_may`).

Конкурентный разбор и правки оффера: `docs/infoproduct_competitive_analysis_2026.md`.
