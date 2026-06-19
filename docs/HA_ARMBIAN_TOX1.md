# Armbian на TOX1 (S905X3) + Home Assistant

**TOX1** — приставка на **Amlogic S905X3**. Главная ветка на 4PDA:  
[TOX1 TV box [Android]](https://4pda.to/forum/index.php?showtopic=1001668) — FAQ, прошивки, **Armbian**, eMMC, DTB.

Официальный [armbian.com](https://www.armbian.com) **часто не** даёт готовый образ «под TOX1» — ставят через инструкции из ветки / **ophub** / общую тему X96.

---

## Какой Armbian ставить

| Вариант | Когда |
|---------|--------|
| **[ophub/amlogic-s9xxx-armbian](https://github.com/ophub/amlogic-s9xxx-armbian)** | **Рекомендуется для TOX1** — есть обсуждения TOX1 / DTB |
| Образ **Armbian 24.x / Debian Bookworm** (aarch64) | Если в релизе явно указан ваш SoC **s905x3** и модель |
| Ubuntu / старый Android на приставке | Только как шаг перед прошивкой eMMC, не как HA |

**Версия:** **Bookworm (Debian 12)** — как у вас сейчас в empire (`armbian` + Docker + HA Supervised).  
**Ядро:** свежее stable из того же репозитория, что в инструкции к образу.

Перед установкой:

| На 4PDA (из шапки темы TOX1) | Зачем |
|------------------------------|--------|
| [Установка Armbian](https://4pda.to/forum/index.php?showtopic=976667&view=findpost&p=102642219) (+ [доп.](https://4pda.to/forum/index.php?act=findpost&pid=119914849&anchor=Spoil-119914849-1)) | основной гайд |
| [Корректный dtb для Armbian на TOX1](https://4pda.to/forum/index.php?showtopic=1001668&view=findpost&p=134103517) | **обязательно** — без DTB сеть/Wi‑Fi могут не работать |
| [Home Assistant на Armbian](https://4pda.to/forum/index.php?showtopic=976667&view=findpost&p=93896875) | HA после Armbian |
| [Бэкап/восстановление eMMC через Armbian](https://4pda.to/forum/index.php?showtopic=976667&view=findpost&p=117598942) | перед экспериментами |
| [Загрузка с MicroSD](https://4pda.to/forum/index.php?showtopic=976667&view=findpost&p=117878185) | первый запуск |

В Issues [ophub/amlogic-s9xxx-armbian](https://github.com/ophub/amlogic-s9xxx-armbian) по **TOX1** — альтернативные образы и DTB.

---

## Куда ставить: eMMC, microSD или USB

| Носитель | Для HA 24/7 | Комментарий |
|----------|-------------|-------------|
| **eMMC (встроенная память)** | **Лучший выбор** | Быстрее, стабильнее, обычно 16–64 ГБ — хватит для HA, Docker, 1–2 локальных бэкапа |
| **microSD** | Только тест | Медленно, износ, риск порчи при отключении питания — **не** для постоянного HA |
| **USB SSD / флешка** | Хорошо | Загрузка с USB 3.0 SSD — компромисс, если eMMC не прошивается |
| **«Виртуальная память» (swap)** | **Не ОС** | Swap — подкачка RAM, **на неё Linux не ставят** |

**Итог для empire:** Armbian + Docker + HA Supervised → **на eMMC**.  
SD — только чтобы **первый раз загрузиться** и запустить установщик на eMMC.

---

## Схема установки (типичная для TV box)

```text
1. Скачать образ Armbian под s905x3 (ophub / инструкция TOX1)
2. Записать на microSD или USB (Balena Etcher, Rufus)
3. Загрузка с SD/USB (кнопка reset / пульт «отключить питание» — см. гайд к боксу)
4. Первый вход: armbian / armbian → смена пароля
5. Установка на eMMC: armbian-install  (или aml_boot / скрипт из README ophub)
6. Выключить питание, вынуть SD — дальше грузится с eMMC
7. apt update, Docker, HA Supervised — как docs/HA_ARMBIAN_DOCKER.md
```

Точные команды — в README **вашего** образа (`armbian-install`, `dd`, recovery из Android и т.д.).

---

## Объём памяти

| Ресурс | Минимум для HA + ZHA + бэкапы |
|--------|-------------------------------|
| **eMMC** | **32 ГБ** комфортно; 16 ГБ — впритык (бэкапы → Google, local retain = 1) |
| **RAM** | 2 ГБ — работает; 4 ГБ — лучше |

После установки сразу:

```bash
df -h
```

Оставьте **≥5 ГБ** свободно под Docker и один локальный бэкап.

---

## Docker и HA — где жить

| Компонент | Где |
|-----------|-----|
| **Armbian** | eMMC (система) |
| **Docker** | на той же eMMC |
| **HA Supervised** | контейнеры Docker на eMMC |
| **Конфиг HA** | `/config` внутри Docker volume (тоже eMMC) |
| **Zigbee `zigbee.db`** | бэкапить в Google / на ПК |

Не разносите систему на SD, а Docker на eMMC — один диск проще и надёжнее.

---

## TOX1 — важно из 4PDA (перед Armbian)

| Тема | Рекомендация |
|------|----------------|
| **Прошивка Android** | У многих **шифрованная** 1.4–1.6 — откат на 1.3 **невозможен**; читать [FAQ про шифрование](https://4pda.to/forum/index.php?showtopic=1001668&view=findpost&p=106378012) |
| **Питание** | **5 V, ≥2 A** — слабый БП = перезагрузки, «зависание на логотипе» |
| **HDMI** | Не воткнуть «на горячую» — выключить ТВ и приставку |
| **Порты** | 1× USB 2.0, 1× USB 3.0, **microSD**, **Gigabit LAN** (RTL8211F) |
| **Прошивка с ПК** | [USB Burning Tool (UBT)](https://4pda.to/forum/index.php?act=findpost&pid=119132440&anchor=tox1_firmware_upgrade_ubt) — если нужно вернуть Android |

## TOX1 — частые проблемы (Armbian / HA)

| Проблема | Что проверить |
|----------|----------------|
| Не грузится | [DTB для TOX1](https://4pda.to/forum/index.php?showtopic=1001668&view=findpost&p=134103517), загрузка с SD/USB |
| Нет Ethernet | DTB; на TOX1 есть **LAN 1000M** — предпочтительнее Wi‑Fi для HA |
| Нет USB для Zigbee | USB 2.0 + **powered hub** |
| Диск забился | `docs/HA_RECOVER_DISK_FULL.md` |

---

## Сравнение с текущим armbian (192.168.1.41)

Если **уже** есть рабочий HA на другой плате — перенос на TOX1:

1. Бэкап HA (когда диск не забит).
2. Новый Armbian на eMMC TOX1.
3. Установка HA Supervised.
4. Restore бэкапа или копирование `/config` + `zigbee.db`.

---

## Связанные файлы

- `docs/HA_ARMBIAN_DOCKER.md`
- `docs/HA_RECOVER_DISK_FULL.md`
- `docs/HA_GOOGLE_DRIVE_BACKUP.md` — **retain local: 1**
- `docs/TZ_HOME_ASSISTANT.md`
