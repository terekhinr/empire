# Citilux Smart → Home Assistant → Алиса

**Бренд:** [Citilux Smart](https://citilux.ru/smart/)  
**Управление для HA / Tuya Cloud:** только через **Smart Life** (не отдельное приложение «Citilux SMART»)  
**Чип:** Wi‑Fi **Tuya** в люстре/светильнике  

В **Link App Account** на platform.tuya.com попадают устройства **только из Smart Life**. Если люстра заведена **только** в приложении Citilux — в списке Tuya её **не будет**.

Инструкция Citilux: [PDF Smart Life](https://bx24.citilux.ru/upload/smart/smart-life.pdf).

---

## Рекомендуемая схема (как у всей квартиры)

```text
Алиса → Yandex Smart Home (Yaha Cloud) → Home Assistant → LocalTuya → люстра Citilux
```

**Не держать два пути:** «Алиса → Smart Life напрямую» и «Алиса → HA» на **одной** лампе — будет путаница и рассинхрон.

После успешного LocalTuya:

1. В «Дом с Алисой» **убрать** дубликат люстры от производителя Tuya/Smart Life/Citilux (если есть второй экземпляр).  
2. Оставить свет только из навыка **Yaha Cloud** (ваш HA).

---

## Шаг 1. Подготовка

| Действие | Зачем |
|----------|--------|
| Люстра уже в **Smart Life** | так и должно быть после покупки |
| Роутер: **постоянный IP** люстры | LocalTuya стабильнее |
| Wi‑Fi **2.4 GHz** | Tuya не работает на 5 GHz |
| В HA **нет** рабочего **Tuya Cloud** | только **LocalTuya** — см. `HA_WIFI_ADD_NOW.md` |

Запишите **модель** с наклейки (например `CL224A161`, `CL703A100G`) — пригодится для выбора DP в LocalTuya.

---

## Шаг 2. LocalTuya в HA

Полный порядок: **`docs/HA_WIFI_ADD_NOW.md`** (разделы 1–3).

Кратко:

1. HACS → **LocalTuya** → установить → перезагрузка HA.  
2. Ключи Tuya — **tinytuya** на armbian или ПК в Wi‑Fi `192.168.1.0/24` (на armbian **только через venv**, см. `HA_WIFI_ADD_NOW.md` §3):

```bash
python3 -m venv ~/tinytuya-venv
~/tinytuya-venv/bin/pip install tinytuya
~/tinytuya-venv/bin/python -m tinytuya wizard
~/tinytuya-venv/bin/python -m tinytuya scan
```

3. Аккаунт **Smart Life** / [iot.tuya.com](https://iot.tuya.com) — разовая привязка в **wizard**.  
4. Из **scan**: IP, **device id**, **local key**, протокол **3.3** / **3.4**.  
5. HA → **Добавить интеграцию** → **LocalTuya** → ввести данные устройства.

Ожидаемый результат в HA:

- сущность **`light.*`** (яркость, часто цветовая температура; при RGB — и цвет);
- иногда дополнительно `switch.*` — смотреть по факту.

---

## Шаг 3. Область и имя

1. **Настройки → Области** — привязать устройство к **нужной детской** (`komnata_semiona` / `komnata_maksa` — как у вас в ТЗ).  
2. **Сущности** — понятное имя, например «Люстра» / «Свет».

---

## Шаг 4. Алиса (через HA)

В `/config/yandex_smart_home.yaml` добавить (подставьте реальный `entity_id`):

```yaml
filter:
  include_entities:
    - light.komnata_semiona_lyustra   # пример

entity_config:
  light.komnata_semiona_lyustra:
    name: Свет
    room: Комната Семёна   # как в Area / как хотите слышать голосом
```

→ **Перезагрузка YAML** → `yandex_smart_home.reload` → в приложении **Дом с Алисой** обновить **Yaha Cloud**.

Фразы:

- «Алиса, **включи свет** в комнате Семёна» (комната = как в `room:`)  
- «Алиса, **сделай свет … на пятьдесят процентов**» — если сущность именно **`light`**

Сценарии режимов («Ночь», «Дети спят») — отдельно, как в `HA_YANDEX_ALICE_SETUP.md`.

---

## Шаг 5. Проверка

| # | Где | Действие |
|---|-----|----------|
| 1 | HA | **Службы** → `light.turn_on` / `turn_off` на новой сущности |
| 2 | HA | Яркость 30% — меняется на люстре |
| 3 | Дом с Алисой | Переключатель из Yaha Cloud |
| 4 | Колонка | «Алиса, включи свет …» |

---

## Если LocalTuya не находит / не управляет

| Симптом | Что попробовать |
|---------|----------------|
| Нет в scan | Лампа онлайн в Smart Life? Тот же Wi‑Fi что HA? |
| Invalid key | Перепройти **tinytuya wizard**, обновить key |
| Только on/off, нет % | В LocalTuya выбрать другой **device type** / DPs для этой модели |
| После обновки прошивки пропало | Снова wizard — key мог смениться |

Альтернатива (хуже): оставить только Smart Life + Алиса **без HA** — тогда эта комната **вне** единого empire-умного дома.

---

## Связь с планом квартиры

| Комната | Citilux Smart |
|---------|----------------|
| Детская с этой люстрой | **Голос через HA** (этот гайд) |
| Ванная / туалет / прихожая | автосвет, **без** Алисы |
| Гостевая / другая детская | **ИК**, не Citilux |

См. `docs/HA_LIGHTING_ALICE_ROADMAP.md`.
