# Добавление Wi‑Fi устройств в Home Assistant (пошагово)

**HA:** `http://192.168.1.41:8123` (Tailscale: `100.80.133.85`)  
**Сейчас в HA:** HACS ✅, Tuya Cloud ❌ `setup_error` → **удалить**, **LocalTuya** ещё нет, **Sonoff** ещё нет.

**Не трогаем ИК:** гостевая и комната Макса — позже (Broadlink).

---

## Порядок (сегодня)

| # | Что | Интеграция |
|---|-----|------------|
| 1 | Удалить **Tuya Cloud** (если ещё есть) | — |
| 2 | **Sonoff BASICR2 ×2** | **SonoffLAN** → гайд **`docs/HA_SONOFF_NOW.md`** |
| 3 | — | **Tuya / LocalTuya — позже** |
| 4 | Розетки: чайник, мультиварка | LocalTuya (когда дойдёте) |
| 5 | Остальные Tuya Wi‑Fi | LocalTuya |
| 6 | Датчик температуры | LocalTuya |
| 7 | Areas + группа «отпуск» | HA UI |

---

## 0. Подготовка сети

На роутере для **каждого** Wi‑Fi устройства:

- **DHCP reservation** (постоянный IP `192.168.1.x`)
- Только **2.4 GHz** Wi‑Fi

Записать таблицу:

| Устройство | IP | device_id | local_key | protocol |
|------------|-----|-----------|-----------|----------|
| Чайник | | | | 3.3 / 3.4 |
| Мультиварка | | | | |
| … | | | | |

---

## 1. Удалить Tuya Cloud

**Настройки** → **Устройства и службы** → **Tuya** → **Удалить**.

(С VPS можно было удалить через API — проверьте, что записи Tuya нет.)

Перезагрузка YAML не обязательна; в журнале не должно быть ошибок Tuya.

---

## 2. Установить LocalTuya (HACS)

1. **HACS** → **Интеграции** → **⋮** → **Пользовательские репозитории**  
   - URL: `https://github.com/rospogrig/localtuya`  
   - или актуальный fork: `https://github.com/make-all/tuya-local` — **не путать:**  
   - для **LocalTuya** классика: `https://github.com/rospogrig/localtuya`  
2. **LocalTuya** → **Установить** → **перезагрузка HA**.
3. **Настройки** → **Добавить интеграцию** → **LocalTuya**.

> Если репозиторий rospogrig недоступен — в HACS поиск **「local tuya」** и смотрите загрузки >10k.

---

## 2.1 Tuya IoT: проект и дата-центр (только если §3 scan не помог)

> **Проще:** сначала **`tinytuya scan`** (§3) — часто хватает без этого раздела.

Сайт: **[platform.tuya.com](https://platform.tuya.com)** → слева **Cloud** → **Development** (не вкладка AI Agent на главной).

Если у проекта **Potertiy** нет дата-центра — проще **создать новый проект**, чем чинить старый:

1. **Create Cloud Project**
2. Тип: **Smart Home**
3. **Data Center:** **Central Europe** (для России / Smart Life)
4. Создать → **Overview** — скопировать Access ID / Secret → wizard

Старый **Potertiy** можно не трогать.

### Шаг A — где выбрать Data Center (если в меню «нет»)

У Tuya **два разных** создания проекта. Нужен **классический Cloud**, не вкладка AI на главной.

1. Откройте напрямую: **[platform.tuya.com/cloud/](https://platform.tuya.com/cloud/)**  
   (или слева **Cloud** → **Development** / «Мои облачные проекты»).
2. **Create Cloud Project** — в окне должны быть поля:
   - **Industry:** Smart Home (умный дом)
   - **Development Method:** **Smart Home** (не Custom / не «своя разработка»)
   - **Data Center:** выпадающий список → **Central Europe Data Center**
3. **Create** → **Authorize** (Smart Home Basic Service и т.п.) → **Authorize**.

Если поля **Data Center** всё равно нет — вы не в том мастере (часто **Custom**). Создайте **новый** проект с **Smart Home**.

Проект **Potertiy** с пустым Data Center в Overview — не чинить, создать новый.

Пока в **Overview** у проекта **Data Center** пусто или **suspended**, wizard даст ошибку **28841107**.

### Шаг A2 — включить облако (если suspended)

1. Проект → **Service API** (или **Authorization**).
2. Подключить **Smart Home Basic Service** / trial **IoT Core** (бесплатный период, если предлагают).
3. **Overview** — поле **Data Center** должно показать **Central Europe**, не пусто.

### Шаг B — какой дата-центр (РФ / Smart Life)

В телефоне **Smart Life** (Citilux):

**Я** → **Настройки** → **Аккаунт и безопасность** → **Регион** (Russia / Россия и т.п.).

| Регион в приложении | Обычно дата-центр в Tuya |
|---------------------|---------------------------|
| **Russia / Россия** | **Central Europe Data Center** |
| EU / Европа | Central Europe или Western Europe |
| USA | Western America |

На **Devices** справа сверху выпадающий список дата-центра — выберите **тот же**, что в Overview.

> Бесплатный аккаунт часто может иметь **один** активный дата-центр на аккаунт. Не создавайте лишние проекты.

### Шаг C — Link Tuya App Account

1. **Devices** → **Link Tuya App Account** (или **Link App Account**).
2. **Add App Account**.
3. Вверху справа — правильный **Data Center**.
4. QR-код → в **Smart Life**: **Я** → сканер / «+» → отсканировать → **Подтвердить вход**.
5. **OK** → в списке появятся **только** устройства из **этого** аккаунта **Smart Life**.

Дальше: **§3** — `tinytuya wizard` (Access ID/Secret с **Overview** проекта).

### Несколько приложений (Citilux, DIGMA, Smart Life)

| Приложение | Видно после Link **Smart Life**? | Что делать |
|------------|----------------------------------|------------|
| **Smart Life** / Tuya Smart | **Да** | основной путь |
| **Citilux SMART** (отдельное) | **Нет** | добавить люстру **в Smart Life** (инструкция Citilux), не только в Citilux |
| **DIGMA SmartLife** | **Нет** (другой аккаунт) | см. ниже |

**Link App Account** в Tuya Cloud = один вход в **Smart Life**, не «все приложения сразу».

**Citilux:** официально свет в **Smart Life** — [новость Citilux](https://citilux.ru/news/umnye-svetilniki-citilux-smart-v-prilozhenii-smart-life/). Если люстра только в приложении Citilux — в облаке Tuya её не будет.

**DIGMA SmartLife** — отдельное OEM-приложение Tuya. Варианты:

1. **Перенести** устройство в **Smart Life** (если модель Tuya и приложение даёт «добавить устройство» / тот же способ пейринга).
2. **`tinytuya scan`** на armbian — устройство в Wi‑Fi часто видно по **IP + ID** даже из Digma; ключ — wizard с тем же Smart Life **или** отдельная попытка, если Digma на том же Tuya-аккаунте не заводится.
3. **Оставить Digma + Алиса** напрямую, в HA не тащить (как временно с Citilux).

---

## 3. Получить local_key (один раз)

### Сначала попробуйте ПРОСТОЙ путь (без Tuya Cloud / без дата-центра)

Облако Tuya (**Link App Account**, дата-центр, QR) — **не обязательно** для LocalTuya, если устройство в той же Wi‑Fi.

На **armbian** (или ПК в `192.168.1.x`):

```bash
python3 -m venv ~/tinytuya-venv
~/tinytuya-venv/bin/pip install tinytuya
~/tinytuya-venv/bin/python -m tinytuya scan
```

В таблице ищите лампу/розетку по **IP** и **имени**. Нужны: **IP**, **ID** (device_id), **Key** (local_key), **Version** (3.3 / 3.4).

→ Сразу в HA: **LocalTuya** → ввести эти поля. **Готово.**

Если в scan **нет Key** или устройства нет — тогда только «длинный» путь §3.1 (облако).

**Citilux / лампа в детской:** пока scan не сработал — можно **оставить Smart Life + Алиса** как сейчас; HA не обязателен срочно.

---

### 3.1 Длинный путь — только если scan не дал Key

### Вариант A — tinytuya wizard (ПК или armbian в той же Wi‑Fi `192.168.1.0/24`)

> **armbian / Debian 12:** `pip install` в системный Python **запрещён** (PEP 668).  
> Не используйте `--break-system-packages` — только **venv** или **pipx** ниже.

#### A1. armbian — venv (рекомендуется)

Один раз:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv ~/tinytuya-venv
~/tinytuya-venv/bin/pip install tinytuya
```

Мастер ключей (аккаунт [iot.tuya.com](https://iot.tuya.com) / Smart Life — разовая регистрация):

```bash
~/tinytuya-venv/bin/python -m tinytuya wizard
```

Скан сети (IP, device id, версия протокола):

```bash
~/tinytuya-venv/bin/python -m tinytuya scan
```

Повторные запуски — те же команды с `~/tinytuya-venv/bin/python`.

#### A2. armbian — pipx (альтернатива)

```bash
sudo apt install -y pipx
pipx ensurepath
# перелогиниться или: source ~/.bashrc
pipx install tinytuya
tinytuya wizard
tinytuya scan
```

#### A3. Windows / Mac в той же Wi‑Fi (если на armbian неудобно)

```bash
python3 -m venv .venv-tuya
# Windows:  .venv-tuya\Scripts\activate
# Linux/Mac: source .venv-tuya/bin/activate
pip install tinytuya
python -m tinytuya wizard
python -m tinytuya scan
```

Вывод scan: `ID` = device_id, `IP`, `Version`, ключи — **сохранить вне git**.

### Вариант B — пока устройство в Digma / Smart Life

Иногда устройства видны только через облачный проект Tuya IoT — тот же wizard.

**Сохраните** `device_id`, `local_key`, `ip`, `protocol_version` в файл (не в git).

---

## 4. Добавить розетку «чайник» (Кухня)

1. LocalTuya → **Add device** (или Configure).
2. **Host:** IP розетки (например `192.168.1.50`).
3. **Device ID**, **Local Key**, **Protocol 3.3** (если не работает — **3.4**).
4. Выбрать тип **switch** / розетка.
5. После появления entity: **Настройки устройства** → **Область: Кухня**.
6. Переименовать: `switch.kuhnya_chainik` (имя сущности).

**Проверка:** выкл/вкл из HA; отключить интернет на роутере на 1 мин — снова переключить (должно работать по LAN).

---

## 5. Розетка «мультиварка» (Балкон)

То же → **Область: Балкон** → `switch.balkon_multivarka`.

---

## 6. Sonoff BASICR2 (2 шт)

Гайд: **`docs/HA_SONOFF_BASICR2.md`**

Кратко:

1. HACS → `https://github.com/AlexxIT/SonoffLAN` → **Sonoff**.
2. eWeLink: оба реле в приложении, фикс. IP.
3. HA → **Sonoff** → логин eWeLink, режим **auto**.
4. Areas: по комнатам (не гостевая/Макс — там ИК).

---

## 7. Белые «Smart Switch» и Digma (Tuya)

Если в **tinytuya scan** видны — только **LocalTuya**, не Digma-приложение для автоматизаций.

Если **не** видны в scan — возможно другой чип; напишите модель.

---

## 8. Датчик температуры

LocalTuya → тип **sensor** / climate sensor (по DP-ID из документации или auto-detect в UI).

**Область:** Балкон. Имя: `sensor.balkon_temperatura`.

Дополнительно: в HA уже есть **Weather** — карточка «улица» на дашборде.

---

## 9. Группа «отпуск» и packages

В `/config/packages/` должны быть:

- `empire_mvp.yaml`
- `empire_automations.yaml`
- `empire_devices.yaml`

**Настройки** → **Группы** → **Техника — выкл. в отпуске** → добавить:

- `switch.kuhnya_chainik`
- `switch.balkon_multivarka`

Тест: **Режим Отпуск** on → розетки off + Telegram.

---

## 10. Яндекс Алиса (после появления switch)

**HACS** → **Yandex Smart Home** → экспорт `switch.*` с именами «Розетка чайник», «Мультиварка».

Подробно: `docs/HA_YANDEX_IR_ALICE.md`.

---

## Чеклист

- [ ] Tuya Cloud удалён
- [ ] LocalTuya установлен
- [ ] tinytuya: ключи для розеток
- [ ] Чайник + мультиварка в HA, areas
- [ ] SonoffLAN: 2× BASICR2
- [ ] Группа отпуска
- [ ] Локальный тест без интернета

---

## Скрипт на armbian (скан Tuya в LAN)

```bash
python3 -m pip install --user tinytuya
python3 -m tinytuya scan
```

Запускать **на armbian** (в той же сети, что и розетки).
