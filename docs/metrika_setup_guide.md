# Яндекс.Метрика: полный гайд для Empire (gdepar.ru)

**Для кого:** настройка с нуля.  
**Сайт с готовым кодом:** [gdepar.ru](https://gdepar.ru) — счётчик и `reachGoal` уже в шаблонах, нужен только **номер счётчика** в env и **цели** в кабинете Метрики.

**Короткая шпаргалка по целям:** `docs/metrika_goals_setup.md`  
**Список всех событий:** `docs/gdepar_ai_assistant_tz.md` §5.1  

**neverretire.ru (Pension):** отдельного счётчика в коде **пока нет** — этот гайд в первую очередь про **gdepar.ru**. Для Пенсии — те же шаги в Метрике + позже добавим `YANDEX_METRIKA_ID` в `web_app.py` (фаза 2).

---

## 1. Как это устроено у нас

```
Посетитель → gdepar.ru (HTTPS)
    → в <head> подключается tag.js (если задан YANDEX_METRIKA_ID)
    → ym(counterId, "init", …)
    → при действиях: gdeparMetrikaReach("имя_цели", {параметры})
    → ym(counterId, "reachGoal", "имя_цели", …)
```

| Компонент | Файл |
|-----------|------|
| Счётчик + базовые цели | `templates/gdepar_metrika.inc.html` |
| Помощник «Пар?» | `templates/gdepar_assistant.inc.html` |
| Карта / попап / отзывы | `templates/gdepar.html`, `gdepar_map.html`, `gdepar_spot.html` |
| ID счётчика с сервера | `gdepar_app.py` → переменная `YANDEX_METRIKA_ID` |
| Prod env | `/etc/empire/gdepar.env` (шаблон: `deploy/gdepar.production.env.example`) |

Пока `YANDEX_METRIKA_ID` **пустой** — на сайте подставляются заглушки (`gdeparMetrikaReach` ничего не шлёт). Это нормально до настройки.

---

## 2. Шаг 1 — аккаунт и счётчик в Яндекс.Метрике

1. Зайдите на [https://metrika.yandex.ru](https://metrika.yandex.ru) под Яндекс ID (лучше тот же, что для Вебмастера / Директа).
2. **Добавить счётчик** (+).
3. Заполните:

| Поле | Значение |
|------|----------|
| Имя счётчика | `gdepar.ru` или «Где пар» |
| Адрес сайта | `https://gdepar.ru` |
| Часовой пояс | `Europe/Moscow` |
| Приём данных на другие домены | Включить, если будете зеркала (`гдепар.рф` редиректит на gdepar.ru — обычно достаточно одного счётчика на каноническом домене) |

4. Рекомендуемые опции при создании (можно включить сразу):

| Опция | Зачем |
|-------|--------|
| **Вебвизор** | Записи сессий — смотреть, где люди «ломаются» на карте |
| **Карта кликов** | Тепловая карта |
| **Отслеживание хеша** | У нас есть якоря `#karta`, `#contacts` — событие `gdepar_hash_section` |
| **E-commerce** | **Не нужен** (нет корзины) |

5. Сохраните. Скопируйте **номер счётчика** — только цифры, например `98765432`.

---

## 3. Шаг 2 — прописать ID на сервере (установка)

Код счётчика **не вставляете вручную** в HTML — только env.

```bash
# На VPS
sudo nano /etc/empire/gdepar.env
```

Добавьте или раскомментируйте строку (только цифры, без кавычек внутри значения в файле env):

```bash
YANDEX_METRIKA_ID=98765432
```

Проверьте, что в основном `.env` проекта **нет** конфликтующей пустой переменной с тем же именем, если `gdepar.env` её не переопределяет — у `empire_gdepar.service` подключены оба файла (`EnvironmentFile`).

Перезапуск:

```bash
sudo systemctl restart empire_gdepar
sudo systemctl status empire_gdepar --no-pager
```

### Проверка, что приложение видит ID

```bash
curl -s http://127.0.0.1:8001/api/gdepar/health | python3 -m json.tool
```

В ответе должно быть:

```json
"metrika_id_set": true
```

Если `false` — ID не подхватился (опечатка, не цифры, не тот env-файл).

---

## 4. Шаг 3 — проверить, что счётчик на сайте

### 4.1. Исходный код страницы

1. Откройте [https://gdepar.ru](https://gdepar.ru) в браузере.
2. **Просмотр кода** (Ctrl+U) или DevTools → Elements.
3. Найдите `mc.yandex.ru/metrika/tag.js` и число счётчика в `ym(98765432, "init"`.

Если видите только заглушку без `tag.js` — `metrika_id_set` ещё false или кэш CDN.

### 4.2. Расширение / отладчик

- Установите расширение **«Яндекс.Метрика»** для Chrome/Firefox — показывает, что счётчик сработал.
- Или в Метрике: **Настройки → Проверка счётчика** → введите URL `https://gdepar.ru`.

### 4.3. Отчёт в реальном времени

Метрика → **Отчёты → Стандартные → Посетители онлайн** (или «В реальном времени»).

Откройте сайт с телефона/другого браузера — через 1–3 минуты должна появиться визитка.

### 4.4. Карта и внутренние страницы

Проверьте отдельно:

- `https://gdepar.ru/map`
- любую карточку бани `/banya/...`

На каждой должен быть тот же счётчик; в целях уходит параметр `page`: `home` | `map` | `spot`.

---

## 5. Шаг 4 — создать цели (JavaScript-события)

Код уже вызывает `reachGoal` с **фиксированными именами**. В кабинете Метрики нужно создать **цели с теми же идентификаторами**.

### 5.1. Как создать одну цель

1. Метрика → ваш счётчик **gdepar.ru**.
2. **Цели** → **Добавить цель**.
3. Тип: **JavaScript-событие** (иногда «Событие», «reachGoal»).
4. **Идентификатор цели** — **точно** как в таблице ниже (латиница, подчёркивания, без пробелов).
5. Название для себя — по-русски, например «Открытие попапа бани».
6. Сохранить.

Повторить для каждой строки из списка (можно не все сразу — см. приоритеты).

### 5.2. Приоритет: минимум на старт (10 целей)

Создайте **в первую очередь** — по ним строятся воронки и KPI из ТЗ:

| № | Идентификатор | Что значит |
|---|---------------|------------|
| 1 | `gdepar_session_start` | Первый визит во вкладке |
| 2 | `gdepar_page_view` | Просмотр страницы (home/map/spot) |
| 3 | `gdepar_popup_open` | Открыл попап бани на карте |
| 4 | `gdepar_reviews_open` | Раскрыл отзывы |
| 5 | `gdepar_summary_request` | Нажал «Дай саммари» |
| 6 | `gdepar_assistant_fab_click` | Кнопка «Пар?» |
| 7 | `gdepar_assistant_submit` | Отправил вопрос помощнику |
| 8 | `gdepar_assistant_reply_ok` | Успешный ответ помощника |
| 9 | `gdepar_assistant_pick_click` | Клик по рекомендации из помощника |
| 10 | `gdepar_phone_click` | Клик «Позвонить» |

### 5.3. Полный список (22+ целей)

Добавляйте по мере необходимости — все уже шлются с сайта:

| Идентификатор | Когда срабатывает |
|---------------|-------------------|
| `gdepar_session_start` | Первый заход в sessionStorage |
| `gdepar_page_view` | DOMContentLoaded, параметр `page` |
| `gdepar_popup_open` | Попап точки на карте/главной |
| `gdepar_reviews_open` | Показать отзывы |
| `gdepar_summary_request` | Запрос саммари отзывов |
| `gdepar_assistant_fab_click` | FAB «Пар?» |
| `gdepar_assistant_open` | Панель помощника открыта |
| `gdepar_assistant_submit` | Отправка вопроса |
| `gdepar_assistant_session_used` | Первый «живой» ответ за вкладку |
| `gdepar_assistant_reply_ok` | Успешный ответ |
| `gdepar_assistant_reply_fail` | Ошибка ответа |
| `gdepar_assistant_rate_limited` | Лимит запросов |
| `gdepar_assistant_pick_click` | Переход по pick из помощника |
| `gdepar_spot_click_out` | Уход на 2GIS/Яндекс/сайт бани |
| `gdepar_phone_click` | Телефон |
| `gdepar_map_filter_submit` | Фильтр на `/map` |
| `gdepar_home_filter_submit` | Фильтр с главной |
| `gdepar_map_list_pick` | Выбор в списке карты |
| `gdepar_popup_full_map_link` | «Полная карта» из попапа |
| `gdepar_spot_page_from_popup` | «Страница бани» из попапа |
| `gdepar_spot_page_map_link` | «На карте» с карточки бани |
| `gdepar_nav_click` | Навигация в шапке/футере |
| `gdepar_home_cta` | CTA на главной |
| `gdepar_bayka_card_click` | Карточка «Байки» |
| `gdepar_contact_click` | Контакты (telegram, email, …) |
| `gdepar_merch_interest` | Мерч (заглушки) |
| `gdepar_hash_section` | Якорь #karta и др. |

**Параметры** (`spot_id`, `page`, `channel`…) в интерфейсе целей Метрики настраиваются опционально (условия на параметры визита) — для старта достаточно самого идентификатора.

---

## 6. Шаг 5 — воронки и отчёты

### 6.1. Воронка «Помощник → действие» (CR1 из ТЗ)

Метрика → **Цели** / **Конверсии** → **Воронка** (название интерфейса может отличаться).

Пример шагов:

1. `gdepar_assistant_submit`
2. Любое из: `gdepar_phone_click`, `gdepar_spot_click_out`, `gdepar_assistant_pick_click`, `gdepar_popup_open`

Окно атрибуции: **в той же сессии** (по умолчанию).

### 6.2. Воронка «Попап → звонок» (CR2)

1. `gdepar_popup_open`
2. `gdepar_phone_click` или `gdepar_spot_click_out` или `gdepar_spot_page_from_popup`

### 6.3. Доля сессий с AI

Сегмент: визиты, в которых было событие `gdepar_assistant_submit`.  
Делите на общее число визитов за период — грубая **доля сессий с AI**.

### 6.4. Карта кликов и Вебвизор

- **Поведение → Карта кликов** — URL `gdepar.ru/map`.
- **Поведение → Вебвизор** — смотреть записи, где пользователь не дошёл до попапа.

В коде при `init` уже включены: `clickmap: true`, `trackLinks: true`, `accurateTrackBounce: true`.

---

## 7. Трафик из Telegram (промо карты)

В постах канала «Где пар» ссылки должны быть с UTM, например:

```text
https://gdepar.ru/map?utm_source=telegram&utm_medium=post&utm_campaign=weekly_map
```

В Метрике:

- **Отчёты → Источники → Метки UTM**
- Или сегмент: `utm_campaign` = `weekly_map`

В Empire в аналитике бота: событие `tg_promo_map_draft` в `analytics.db` (черновик промо), на сайте — UTM.

**Проверка:** откройте ссылку с UTM с телефона → в Метрике через несколько минут в отчёте «Источники» должен появиться `telegram / post`.

---

## 8. Cloudflare и HTTPS

Сайт за Cloudflare (см. `deploy/nginx/empire_hub`):

- Счётчик грузится с `mc.yandex.ru` — **не блокируйте** этот домен в CF.
- В Метрике в настройках счётчика укажите канонический URL **`https://gdepar.ru`**.
- При режиме SSL **Flexible** на origin nginx уже учтён `X-Forwarded-Proto` — на посещения это не влияет, если пользователь видит HTTPS.

---

## 9. Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| `metrika_id_set: false` | Нет ID в env / не цифры | Проверить `/etc/empire/gdepar.env`, restart |
| Нет `tag.js` в HTML | То же | curl health + view-source |
| Визиты есть, целей нет | Цели не созданы в кабинете | §5 — JavaScript-события |
| Цели не срабатывают | Опечатка в идентификаторе | Сверить с таблицей **буква в букву** |
| Adblock | Блокирует Метрику | Проверять без блокировщика / Вебвизор |
| Дубль счётчика | Вставили ещё один вручную | У нас один include — лишнее убрать |
| 0 визитов с VPS curl | curl не выполняет JS | Проверять браузером, не curl |

### Ручная проверка цели в консоли браузера

На gdepar.ru откройте DevTools → Console:

```javascript
gdeparMetrikaReach('gdepar_page_view', { page: 'home' });
```

Через минуту в Метрике → **Отчёты → Конверсии** — должно появиться достижение `gdepar_page_view` (если цель создана).

---

## 10. neverretire.ru (Pension) — отдельно

Сейчас **счётчик в `web_app.py` не подключён**. План:

1. Создать **второй счётчик** в Метрике на `https://neverretire.ru`.
2. Добавить в код шаблон (аналог `gdepar_metrika.inc.html`) + `YANDEX_METRIKA_ID` в env веб-приложения.
3. Цели: `pension_page_view`, клики по статьям, UTM с YouTube (`utm_source=youtube`).

Пока для Пенсии используйте:

- **Дзен** (встроенная статистика канала)
- **ВК** (статистика сообщества)
- **YouTube Studio** (после запуска канала — `docs/pension_youtube_launch_guide.md`)

---

## 11. Чеклист «Метрика запущена»

- [ ] Счётчик создан на [metrika.yandex.ru](https://metrika.yandex.ru)
- [ ] `YANDEX_METRIKA_ID=…` в `/etc/empire/gdepar.env`
- [ ] `systemctl restart empire_gdepar`
- [ ] `curl …/health` → `"metrika_id_set": true`
- [ ] В исходнике gdepar.ru есть `metrika/tag.js`
- [ ] Визит виден в «Посетители онлайн»
- [ ] Создано ≥10 JS-целей из §5.2
- [ ] Тест `gdeparMetrikaReach` в консоли → конверсия в отчёте
- [ ] Ссылка из TG с UTM → видно в «Метки UTM»
- [ ] Воронки CR1/CR2 набросаны в интерфейсе

---

## 12. Что прислать разработчику

Достаточно **одного числа**:

```text
YANDEX_METRIKA_ID=12345678
```

Можно вставить в `/etc/empire/gdepar.env` сами по §3 — код менять не нужно.

---

*Обновлять при добавлении Метрики на neverretire.ru или новых `reachGoal` в шаблонах.*
