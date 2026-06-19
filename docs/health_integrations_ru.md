# Здоровье и планирование: интеграция с Garmin, Zepp, калориями и Android

Дашборд: **https://neverretire.ru/hub/** → **Личное** → **Здоровье** / **Планирование**.

Данные на VPS лежат в `data/pension/body/` и подхватываются автоматически при изменении файлов (вкладка **Здоровье → Импорт**).

---

## Общая схема (рекомендуется)

```text
Телефон / ПК
  ├─ Garmin Connect      → CSV активностей
  ├─ Zepp Life / весы    → CSV веса и состава тела
  ├─ Lifesum / дневник   → CSV питания
  └─ Obsidian Life/tasks → inbox.md (планирование)
           ↓
   Яндекс.Диск (папка-сборник)
           ↓
   VPS: rclone (cron каждые 6 ч)
           ↓
   Empire dashboard (Streamlit)
```

Почему так: у Garmin **нет нормального бесплатного API** для личного использования; у Lifesum **нет открытого API** для обычных пользователей. Самый стабильный путь — **экспорт CSV + синхронизация папки**.

Скрипты на VPS:

| Скрипт | Назначение |
|--------|------------|
| `scripts/health_sync_from_yandex.sh` | Garmin + весы + еда → `data/pension/body/` |
| `scripts/planning_sync_from_yandex.sh` | `Life/tasks/inbox.md` → дашборд «Планирование» |

---

## 1. Garmin (бег, плавание, зал с часов)

### Что уже работает

Дашборд читает файл в формате вашего `Activities (6).csv` (колонки на русском: «Тип занятия», «Дата», «Расстояние», «Калории», «Время»).

### Способ A — вручную с сайта (надёжно)

1. Откройте **https://connect.garmin.com** (логин как в приложении).
2. **Активности** → выберите период (например, последние 12 месяцев).
3. Экспорт / отчёт → **CSV** (если в интерфейсе нет кнопки — см. способ B).
4. Сохраните как `Activities.csv`.
5. Положите в Яндекс.Диск: `Empire/health-inbox/garmin/Activities.csv`.

На VPS (или по cron):

```bash
sudo bash /root/projects/empire/scripts/health_sync_from_yandex.sh
```

Либо просто обновите страницу **Здоровье** — импорт сработает, если файл уже в `data/pension/body/`.

### Способ B — приложение Garmin Connect (Android)

В мобильном приложении **полного экспорта всех активностей в CSV обычно нет**. Практика:

- отдельные тренировки можно **поделиться** (GPX/TCX) — для дашборда неудобно;
- для сводной статистики лучше **раз в 1–2 недели** экспорт с **сайта** (способ A);
- альтернатива: синхронизация Garmin → **Strava** → экспорт из Strava (если уже пользуетесь).

### Способ C — автоматизация с ПК (полуавтомат)

На домашнем ПК (Windows/Linux), раз в неделю:

- [garmin-connect-export](https://github.com/pe-st/garmin-connect-export) или аналог;
- выход: `activities.csv` → копия в `Empire/health-inbox/garmin/` на Яндекс.Диске.

> **Важно (2026):** неофициальные библиотеки (garth и др.) часто ломаются из‑за защиты Garmin. Для личного дашборда **CSV + Яндекс.Диск** стабильнее, чем прямой API.

### Частота обновления

| Активность | Рекомендация |
|------------|----------------|
| Бег 3×/нед | экспорт раз в 7–14 дней |
| После соревнования / длинной тренировки | можно сразу |

---

## 2. Вес и состав тела (Zepp Life, Mi Fit, умные весы)

### Рекомендуемая схема (автоматически, 0 ₽)

```text
Zepp Life (весы Xiaomi)
    → Google Fit          (Профиль → Add accounts → Google Fit)
    → Intervals.icu       (у вас уже подключён Google Fit)
    → VPS intervals_sync  (кнопка в дашборде / cron)
```

Дополнительно (вес + % жира в дашборд быстрее):

```text
Zepp Life → Google Fit → Health Connect
    → HC Webhook app → POST https://neverretire.ru/api/health/ingest
```

На VPS в `.env`: `HEALTH_INGEST_TOKEN=...` · заголовок в HC Webhook: `X-Health-Token`.

### Mi Fitness

Разовый перенос истории: Mi Fitness → Профиль → **Сторонние данные** → Zepp Life → **Перенести**.  
Постоянная синхронизация через Mi Fitness **не нужна**, если весы уже в Zepp Life.

### Что уже работает

Файлы `BODY_*.csv` с колонками `time,weight,fatRate,muscleRate,visceralFat,...` — как у вас в `data/pension/body/`.

На графиках **вес &lt;90 и &gt;120 кг отбрасывается** (ошибки весов).

### Zepp Life (Android)

1. Весы должны быть привязаны к **Zepp Life** (бывший Mi Fit).
2. Данные копятся в облаке Zepp автоматически при каждом взвешивании.
3. **Экспорт на телефон:**
   - **Профиль → Настройки → Безопасность / Конфиденциальность → Экспорт данных** (название может отличаться по версии);
   - либо через **поделиться отчётом** / email-выгрузку, если есть в вашей версии;
   - цель — получить **CSV с историей веса** (и по возможности % жира).
4. Переименуйте в `BODY_export.csv` и положите в  
   `Яндекс.Диск/Empire/health-inbox/scale/BODY_export.csv`.

### Если экспорт из Zepp неудобен

| Вариант | Как |
|---------|-----|
| **Ручные замеры** | Дашборд → **Здоровье → Записать** (вы уже ведёте талию/бицепс — отлично) |
| **Google Fit** | Zepp → синхронизация в Google Fit → экспорт через Google Takeout (редко, тяжело) |
| **Само приложение весов** | Некоторые весы шлют CSV по email — настройте на свой ящик и скрипт на ПК |

### Частота

- Взвешивание: **1–3 раза в неделю** (утром, натощак).
- Экспорт CSV: **раз в 2–4 недели** или после пачки новых замеров.

---

## 3. Калории (Lifesum и альтернативы)

### Рекомендуемая схема (автоматически)

```text
Lifesum (дневник еды)
    → Health Connect      (Настройки → Automatic Tracking → Health Connect)
    → HC Webhook app      (каждые 30–60 мин)
    → VPS /api/health/ingest
    → дашборд «Здоровье»
```

**Важно:** в Lifesum отключите **Multimodal Tracking** — иначе часть приёмов пищи не экспортируется в Health Connect.

**HC Webhook на телефоне:**
- URL: `https://neverretire.ru/api/health/ingest`
- Custom header: `X-Health-Token: <HEALTH_INGEST_TOKEN из .env>`
- Типы данных: **Nutrition** (обязательно), Weight / Body fat — по желанию

После изменения `.env` перезапустите `empire_webapp`:  
`sudo systemctl restart empire_webapp`

### Ваш текущий формат

`food.csv` с колонками `date, meal_type, title, calories, protein, fat, carbs` — дашборд уже умеет агрегировать по дням.

### Lifesum

Официального **личного API нет**. Варианты:

1. **Экспорт из приложения** (если есть в вашей подписке):  
   Настройки → данные / экспорт → CSV → `Empire/health-inbox/food/food.csv`.
2. **Продолжать вести в Lifesum**, раз в неделю выгружать CSV на Диск (как сейчас по сути и сделано).
3. Если экспорта нет — см. альтернативы ниже.

### Что могу подключить по API (если решите сменить или дублировать дневник)

| Сервис | API | Плюсы | Минусы |
|--------|-----|-------|--------|
| **FatSecret** | Да, [platform.fatsecret.com](https://platform.fatsecret.com) | дневник, вес, OAuth | нужна регистрация разработчика, **whitelist IP VPS**, US dataset на free tier |
| **Cronometer** | Экспорт CSV, API ограничен | точные макросы | платный Pro для экспорта |
| **MyFitnessPal** | Нет нормального public API | привычный интерфейс | только ручной экспорт |
| **Lifesum** | Нет для личного use | удобное UI | только CSV вручную |

**Практическая рекомендация:** оставить **Lifesum + еженедельный CSV** в `health-inbox/food/`. Это проще, чем FatSecret API, и уже совместимо с дашбордом.

Если захотите FatSecret позже — напишите, добавим модуль `fatsecret_sync.py` (OAuth + `food_entries.get_month` на VPS).

---

## 4. Настройка Яндекс.Диск → VPS

### 4.1. Структура папок на Диске

```text
Empire/health-inbox/
  garmin/Activities.csv
  scale/BODY_1770152199658.csv    # любое имя BODY_*.csv
  food/food.csv

Life/tasks/                       # уже есть для Obsidian
  inbox.md
  dashboard.md
```

### 4.2. rclone на VPS (один раз)

```bash
cd /root/projects/empire
sudo bash scripts/rclone_setup_yandex_webdav.sh
```

В `/etc/empire/rclone.env`:

```bash
YANDEX_DISK_USER="ваш@email.ru"
YANDEX_DISK_APP_PASSWORD="пароль_приложения"
YANDEX_HEALTH_REMOTE_PATH="Empire/health-inbox"
YANDEX_LIFE_TASKS_PATH="Life/tasks"
```

Проверка:

```bash
sudo bash scripts/health_sync_from_yandex.sh
sudo bash scripts/planning_sync_from_yandex.sh
```

### 4.3. Cron

```cron
15 6,12,18,23 * * * /root/projects/empire/scripts/health_sync_from_yandex.sh >> /var/log/empire-health-sync.log 2>&1
30 */2 * * * /root/projects/empire/scripts/planning_sync_from_yandex.sh >> /var/log/empire-planning-sync.log 2>&1
```

---

## 5. Планирование (TickTick / Obsidian → дашборд)

### На телефоне и ПК (как сейчас)

- **Obsidian** + плагин **Tasks**, папка `Life/tasks/`.
- Формат: `- [ ] Задача 📅 2026-06-20 #здоровье`
- Теги `#Цели`, `#Проекты` — распознаются при импорте.

### Связка с дашбордом

| Действие | Где |
|----------|-----|
| Добавить задачу с телефона | Obsidian → `inbox.md` (через Яндекс.Диск) |
| Импорт в дашборд | **Планирование** (авто при первом открытии сессии) или кнопка «Импорт из inbox.md» |
| Экспорт обратно | **Планирование → Obsidian** → `dashboard-sync.md` |
| Канвас целей | вкладка **Канвас** в «Планирование» |

### Напоминания на Android

- **Obsidian** — плохо пинает по времени.
- **Tasks.org** — для задач **с точным временем** (будильник).
- Схема: план в Obsidian/дашборде, пинок в Tasks.org.

Подробнее: `docs/obsidian_tasks_ticktick_ru.md`.

---

## 6. Мобильный вид под Android

Отдельное приложение **не обязательно** — дашборд адаптирован под узкий экран.

### Установка «как приложение»

1. Chrome на Android → **https://neverretire.ru/hub/**
2. Логин/пароль (см. `docs/dashboard_access.md` на VPS).
3. Меню Chrome → **Добавить на главный экран**.
4. Раздел **Личное** → **Здоровье** или **Планирование**.

### Что удобно делать с телефона

| Задача | Вкладка |
|--------|---------|
| Записать вес, талию, бицепс | Здоровье → **Записать** |
| Записать силовую | Здоровье → **Записать** |
| Посмотреть графики | Здоровье → **Обзор** |
| Добавить задачу | Планирование → **Добавить** |
| Список дел на сегодня | Планирование → **Доска** |

### Экспорты с телефона без ПК

1. Экспорт CSV из Garmin / Zepp / Lifesum → «Поделиться» → **Яндекс.Диск** → нужная папка `health-inbox/...`.
2. Подождать cron или открыть **Здоровье** на дашборде.

---

## 7. Чеклист «всё подключено»

- [ ] Папка `Empire/health-inbox/` на Яндекс.Диске создана
- [ ] `rclone` на VPS настроен (`scripts/rclone_setup_yandex_webdav.sh`)
- [ ] Cron для `health_sync_from_yandex.sh` и `planning_sync_from_yandex.sh`
- [ ] Garmin: Intervals.icu подключён + «Скачать старые данные»
- [ ] Zepp Life → Google Fit включён
- [ ] Google Fit → Health Connect включён (в приложении Google Fit)
- [ ] Lifesum → Health Connect (экспорт питания)
- [ ] HC Webhook → `https://neverretire.ru/api/health/ingest` + `X-Health-Token`
- [ ] Cron: `intervals_sync.sh` и `health_sync_from_yandex.sh`
- [ ] Весы: Zepp → Google Fit / Intervals (или CSV в `scale/`)
- [ ] Еда: Lifesum → HC Webhook (или `food.csv` раз в неделю)
- [ ] Android: ярлык **neverretire.ru/hub** на главном экране
- [ ] Obsidian `inbox.md` синхронизируется → **Планирование** на дашборде

---

## 8. Дорожная карта (если захотите глубже)

| Этап | Что | Сложность |
|------|-----|-----------|
| ✅ Сейчас | CSV + Яндекс.Диск + автоимпорт | низкая |
| 🔜 | FatSecret API вместо/вместе с Lifesum | средняя |
| 🔜 | PWA manifest (иконка, полноэкранный режим) | низкая |
| ⏳ | Garmin прямой API | высокая, нестабильно в 2026 |
| ⏳ | Health Connect / Google Fit hub | средняя, только Android |

Когда будете готовы к FatSecret или PWA — напишите, сделаем следующим шагом в коде.
