# Teckin TC100 → бесплатный RTSP для Home Assistant

Модель: **Teckin TC100** (FCC `2AQNX-TC100`, SoC **Anyka AK3918**).

Полноценной замены прошивки на OpenIPC для AK3918 **нет**. Рабочий путь — **SD-card hack**: камера уже на Linux; при загрузке с microSD поднимаются RTSP, веб-интерфейс, ONVIF, FTP. Облако Teckin отключается, пока карта в слоте.

Источник: [TECKIN-TC100-Anyka-AK3918-camera-hacks](https://github.com/ThatUsernameAlreadyExist/TECKIN-TC100-Anyka-AK3918-camera-hacks) (клон в `hack-files/`).

## Что нужно

- 2× microSD (по одной на камеру), до 32 ГБ
- Карты отформатировать **FAT32**, размер кластера **32 КБ** (16 КБ и меньше — нестабильно)
- Камеры подключены к Wi‑Fi (через приложение Teckin) **или** файл `wpa_supplicant.conf` на карте

## Быстрый старт (Linux)

```bash
cd scripts/teckin-tc100
chmod +x prepare-sdcard.sh

# Вариант A: карта уже FAT32 с кластером 32K — только скопировать файлы
sudo mount /dev/sdb1 /mnt
sudo ./prepare-sdcard.sh copy-only /mnt
sudo umount /mnt

# Вариант B: отформатировать целый диск и залить файлы
sudo ./prepare-sdcard.sh format /dev/sdb

# Wi‑Fi без приложения Teckin:
WIFI_SSID="MyHome" WIFI_PSK="password" sudo ./prepare-sdcard.sh copy-only /mnt
```

### Windows

1. Отформатировать карту: **FAT32**, allocation unit **32768** (32 KB).
2. Скопировать **всё содержимое** папки `hack-files/` в корень карты.
3. Опционально: `wpa_supplicant.conf` по образцу `hack-files/wpa_supplicant.conf.dist`.

## Установка на камеру

### Вариант A — без приложения Teckin (рекомендуется, если пейринг не работает)

1. Подготовить microSD (FAT32, кластер 32 КБ) + скопировать `hack-files/`.
2. Создать в **корне карты** файл `wpa_supplicant.conf` с SSID и паролем 2.4 GHz Wi‑Fi:
   ```bash
   ./make-wpa-conf.sh /path/to/mounted/sdcard/wpa_supplicant.conf
   ```
3. **Без SD карты** камера не настроена — это нормально. Вставить карту, включить питание.
4. Через 1–3 мин проверить в роутере новое устройство (MAC Wi‑Fi) или `nmap -sn 192.168.x.0/24`.
5. Открыть `https://IP` (логин `root`/`pass`).

Приложение Teckin для RTSP **не нужно**.

### Вариант B — через приложение Teckin

1. **SD карту не вставлять** до успешного пейринга.
2. Подключить камеру к Wi‑Fi (приложение Teckin) и узнать IP в роутере.
3. Вставить подготовленную microSD, перезагрузить камеру.

## Пейринг в Teckin не проходит

Типичная жалоба: QR отсканировали, «пейринг» крутится и тишина. Частые причины:

| Проверка | Что сделать |
|----------|-------------|
| **2.4 GHz** | TC100 не видит 5 GHz. Телефон на **той же** 2.4 сети, что прописываете в приложении. |
| **Один SSID** | На Keenetic/других: временно отключить 5 GHz или развести имена (`Home` / `Home_5G`), иначе телефон уходит на 5 GHz. |
| **WPA2-PSK** | Не WPA3-only, не Enterprise. В роутере: WPA2-PSK (AES). |
| **VPN / Private DNS** | Выключить на телефоне (AdGuard, NordVPN и т.д.). |
| **iPhone** | Настройки → Teckin → **Локальная сеть** — включить. |
| **Расстояние** | Камера в 1–2 м от роутера на время настройки. |
| **Сброс** | Кнопка reset 5–10 с до быстрого мигания → снова QR. |
| **Режим AP** | В приложении (часто ⋮ справа сверху) — «AP mode» / ручная привязка. |
| **SD в слоте** | Вынуть карту — с хаком облако Teckin не работает. |
| **Сервис Teckin** | У приложения бывают сбои; отзывы в Play Store про зависание после пейринга. |

**Практичный обход:** не мучить Teckin — сразу **вариант A** (SD + `wpa_supplicant.conf`). Это как раз цель (RTSP в HA).

После загрузки с картой смотреть `log/startup.log` на microSD — там видно, поднялся ли Wi‑Fi.

## Проверка

| Сервис | Адрес |
|--------|--------|
| RTSP main | `rtsp://IP:554/video0_unicast` |
| RTSP sub | `rtsp://IP:554/video1_unicast` |
| Веб-UI | `https://IP` |
| Логин | `root` / `pass` (сменить в настройках веб-UI) |

```bash
ffplay -rtsp_transport tcp rtsp://root:pass@192.168.1.50:554/video0_unicast
```

## Home Assistant

**Generic Camera** (`configuration.yaml`):

```yaml
camera:
  - platform: generic
    name: Teckin TC100 гостиная
    still_image_url: https://root:pass@192.168.1.50/cgi-bin/currentpic.cgi
    stream_source: rtsp://root:pass@192.168.1.50:554/video0_unicast
    verify_ssl: false
```

Или через UI: **Настройки → Устройства → Добавить интеграцию → Generic Camera**.

**ONVIF** (если включён в autostart на карте — по умолчанию да): интеграция ONVIF, порт 80, логин `root`/`pass`.

**Frigate / go2rtc**: добавить RTSP URL как источник; для субпотока — `video1_unicast` (меньше нагрузка).

## Две камеры

Одинаковые файлы на обе карты. Разные IP — через роутер. Имена в HA — разные (`Teckin зал`, `Teckin кухня`). При желании на каждой карте свой `config/hostname.conf` (после первого копирования отредактировать на карте).

## Откат

Вынуть microSD и перезагрузить — снова облачный режим Teckin.

## Если hack не сработал

1. **Кластер 32 КБ** — самая частая причина.
2. Убедиться, что модель **TC100** с чипом AK3918 (ваши наклейки совпадают).
3. Лог на карте: `log/startup.log` после загрузки.
4. Железный путь (UART + U-Boot, бэкап/прошивка flash): [Tengo10/TC100-mod](https://github.com/Tengo10/TC100-mod) — только при опыте с паяльником/serial.

## Безопасность

- Сменить пароль `root` в веб-интерфейсе.
- Камеры только в локальной сети/VLAN; не пробрасывать RTSP в интернет без VPN.
