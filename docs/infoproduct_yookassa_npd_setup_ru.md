# П.1 — Полный гайд: НПД + ЮKassa + VPS (Empire)

Пошаговая инструкция для приёма оплаты инфопродуктов **Garden** и **Stern** через Empire на сервере.

**Связанные файлы:** `empire_sales.py`, `sales.db`, `deploy/nginx/pay_neverretire.conf`, `data/empire_flags.json`.

**Важно:** на май 2026 в коде есть **webhook-каркас** (логирует события), но **создание платежа из бота** (`create_payment`) ещё не подключено. До доработки кода продажи во ВК можно вести **вручную** (см. [гайд ВК](garden_vk_sales_funnel_ru.md), фаза A). Этот документ готовит инфраструктуру, чтобы в день подключения API осталось только включить флаги.

---

## Что понадобится заранее

| Что | Зачем |
|-----|--------|
| Паспорт, ИНН | Регистрация самозанятого |
| Смартфон с приложением **«Мой налог»** | НПД, чеки, лимит 2,4 млн ₽/год |
| **Расчётный счёт** или карта для ИП/физлица, которую примет ЮKassa | Выплаты с эквайринга |
| Доступ к DNS домена **neverretire.ru** | Поддомен `pay.neverretire.ru` |
| SSH на VPS Empire | `systemctl`, nginx, `.env` |

**Отдельная «карта для инфопродукта» не нужна** — нужен расчётный счёт/выплаты в личном кабинете ЮKassa.

---

## Этап 1. Самозанятость (НПД)

### 1.1 Регистрация

1. Установите **«Мой налог»** (ФНС): [nalog.ru](https://nalog.ru) → самозанятые.  
2. Зарегистрируйтесь как плательщик НПД (паспорт, ИНН, при необходимости фото).  
3. Выберите регион деятельности (где фактически оказываете услуги / продаёте цифровые товары).

### 1.2 Виды деятельности

Для PDF-гайдов и онлайн-курсов обычно подходят формулировки вроде:

- продажа информационных материалов / консультационные услуги дистанционно  

**Проверьте в приложении** актуальный список видов дохода — формулировки меняются.

### 1.3 Чеки

- При оплате через **ЮKassa (тариф для самозанятых)** чек в ФНС часто формируется **автоматически** интеграцией.  
- При **ручном переводе на карту** чек нужно пробить **вручную** в «Мой налог» (иначе риск для НПД).

### 1.4 Лимит

- **~2 400 000 ₽** выручки в год на НПД.  
- Empire считает приближение: `EMPIRE_NPD_ANNUAL_LIMIT_RUB` в `.env`, алерт в `GET /health` сервиса sales.

---

## Этап 2. ЮKassa (магазин)

### 2.1 Регистрация

1. [yookassa.ru](https://yookassa.ru) → подключение.  
2. Выберите режим **самозанятый** (не «просто ИП», если вы на НПД).  
3. Привяжите **ИНН** из «Мой налог».  
4. Укажите **сайт** (можно `https://neverretire.ru` или заглушку лендинга).  
5. Пройдите модерацию (обычно 1–3 рабочих дня).

### 2.2 Что получите после одобрения

| Параметр | Где взять |
|----------|-----------|
| **shopId** (идентификатор магазина) | Настройки → Интеграция → Ключи API |
| **Секретный ключ** | Там же (показывается один раз — сохраните) |
| Тестовый магазин | Отдельные test-ключи для отладки |

### 2.3 Webhook в кабинете ЮKassa

1. **Интеграция** → **HTTP-уведомления** (webhooks).  
2. URL:  
   ```text
   https://pay.neverretire.ru/webhook/yookassa
   ```  
3. События (минимум):  
   - `payment.succeeded`  
   - `payment.canceled` (опционально)  
   - `refund.succeeded` (если будут возвраты)  
4. Секрет webhook (если ЮKassa даёт отдельный) — тот же смысл, что `YOOKASSA_WEBHOOK_SECRET` в Empire.

### 2.4 Тестовый платёж

1. Включите **тестовый режим** в кабинете.  
2. Используйте [тестовые карты ЮKassa](https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing).  
3. После успеха в логах VPS должно появиться событие (см. этап 4).

---

## Этап 3. DNS и nginx на VPS

### 3.1 DNS

У регистратора домена `neverretire.ru`:

| Тип | Имя | Значение |
|-----|-----|----------|
| A | `pay` | IP вашего VPS |

Проверка: `dig +short pay.neverretire.ru`

### 3.2 Nginx

В репозитории: `deploy/nginx/pay_neverretire.conf`

```bash
sudo cp /root/projects/empire/deploy/nginx/pay_neverretire.conf \
  /etc/nginx/sites-available/pay.neverretire.ru
sudo ln -sf /etc/nginx/sites-available/pay.neverretire.ru \
  /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3.3 SSL (Let's Encrypt)

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d pay.neverretire.ru
```

Раскомментируйте блок `listen 443 ssl` в конфиге nginx, подставьте пути к сертификатам, снова `nginx -t && reload`.

### 3.4 Проверка снаружи

```bash
curl -sS https://pay.neverretire.ru/health
```

Ожидаемый ответ (пример):

```json
{"status":"ok","stop_sales":true,"npd":{...}}
```

Пока `stop_sales: true` — webhook отклоняет оплаты (это нормально до запуска).

---

## Этап 4. Сервис `empire_sales` на VPS

### 4.1 Переменные окружения

Добавьте в `/etc/empire/empire.env` (или `/root/projects/empire/.env`, chmod 600):

```bash
# ЮKassa (после модерации магазина)
YOOKASSA_SHOP_ID=ваш_shopId
YOOKASSA_SECRET_KEY=live_...
YOOKASSA_WEBHOOK_SECRET=длинная_случайная_строка

EMPIRE_SALES_PORT=8002
EMPIRE_SALES_DB=/root/projects/empire/sales.db
EMPIRE_NPD_ANNUAL_LIMIT_RUB=2400000
```

Секрет webhook должен совпадать с тем, что проверяет nginx/приложение (заголовок `X-Webhook-Secret` в `empire_sales.py`).

Обновите `.env.example` у себя локально — **не коммитьте** live-ключи.

### 4.2 Systemd

```bash
sudo cp /root/projects/empire/deploy/empire_sales.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable empire_sales
sudo systemctl start empire_sales
sudo systemctl status empire_sales
```

Логи: `journalctl -u empire_sales -f`

### 4.3 Синхронизация каталога

При старте `init_sales_db()` подтягивает товары из:

- `data/stern_products.json`  
- `data/garden_products.json`  

Проверка:

```bash
curl -sS http://127.0.0.1:8002/products | python3 -m json.tool
```

---

## Этап 5. Включение продаж (когда код готов)

### 5.1 Флаг стопа

`data/empire_flags.json`:

```json
{
  "stop_sales": false
}
```

Или через код/дашборд, если есть обёртка `save_empire_flags`.

### 5.2 Товары

В `data/garden_products.json` / `data/stern_products.json`:

```json
"payments_enabled": true
```

Перезапуск ботов (подтянут каталог из БД):

```bash
sudo systemctl restart empire_garden_bot empire_stern_bot
```

### 5.3 Боты

| Бот | Env | Unit |
|-----|-----|------|
| Сад | `GARDEN_BOT_TOKEN`, `EMPIRE_GARDEN_BOT_USERNAME` | `empire_garden_bot` |
| Штерн | `STERN_BOT_TOKEN` | `empire_stern_bot` |

Сейчас при `payments_enabled: true` garden-бот отвечает «Оплата подключается» — до реализации ссылки ЮKassa в `empire_garden_bot.py`.

---

## Этап 6. Чеклист «готов к первой реальной оплате»

- [ ] НПД активен, лимит отслеживаете  
- [ ] ЮKassa модерация пройдена, live-ключи в `empire.env`  
- [ ] `https://pay.neverretire.ru/health` → `status: ok`  
- [ ] Webhook в кабинете ЮKassa → URL 200 (тестовое уведомление)  
- [ ] `stop_sales: false`  
- [ ] `payments_enabled: true` на нужном SKU  
- [ ] Тестовая оплата 1 ₽ / тестовая карта → запись в `orders`, выдача PDF/урока  
- [ ] Чек появился в «Мой налог»  
- [ ] Событие в `analytics.db` (`garden_order_paid` / аналог для stern)

---

## Этап 7. Пока API оплаты в боте не готов (переходный режим)

| Канал | Как продавать сейчас |
|-------|----------------------|
| **ВК** | Сообщения сообщества → перевод / счёт ЮKassa вручную → PDF в ответ ([гайд ВК](garden_vk_sales_funnel_ru.md)) |
| **TG-бот** | `/waitlist` + ручная выдача файла админом |
| **После доработки** | Кнопка «Оплатить» → ссылка ЮKassa → webhook → авто-выдача PDF |

Записывайте ручные продажи в таблицу (дата, сумма, продукт, `source_id`) — для НПД и для будущей сверки с `orders`.

---

## Частые ошибки

| Симптом | Решение |
|---------|---------|
| Webhook 401 | Неверный `YOOKASSA_WEBHOOK_SECRET` / заголовок |
| Webhook 503 `stop_sales` | `"stop_sales": false` в `empire_flags.json` |
| 502 Bad Gateway | `systemctl status empire_sales`, порт 8002 |
| Чек не ушёл в ФНС | Тариф ЮKassa «для самозанятых», не обычный ИП-тариф |
| Двойной чек | Не бить вручную в «Мой налог», если ЮKassa уже отправила |

---

## Следующий шаг после этого гайда

1. Завтра: [оформление ВК и продажи вручную](garden_vk_sales_funnel_ru.md).  
2. Параллельно: регистрация НПД + заявка в ЮKassa.  
3. Когда придут ключи — этапы 3–4 на VPS.  
4. Запрос в разработку: endpoint `POST /payments/create` + выдача PDF в garden/stern ботах.

*Обновлено: май 2026*
