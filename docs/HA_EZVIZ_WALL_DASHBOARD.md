# Настенная панель HA + камеры Ezviz

Тёмная панель в стиле референсов (планшет на стене): камеры, климат, свет, безопасность, домофон.

**Файлы в репозитории:**

| Файл | Назначение |
|------|------------|
| `homeassistant/themes/empire_wall.yaml` | Тёмная тема, акцент `#00d4aa` |
| `homeassistant/dashboards/empire_wall.yaml` | Дашборд «Панель» (3 вкладки) |
| `homeassistant/packages/empire_ezviz.yaml` | Telegram при движении на камерах |
| `deploy/ha_deploy_wall_dashboard.sh` | Деплой на armbian |

Старый дашборд по комнатам (`empire_main.yaml`) **не трогаем** — «Панель» идёт отдельной вкладкой в сайдбаре.

---

## 1. Подключить Ezviz (две камеры)

1. Убедитесь, что камеры добавлены в приложение **Ezviz** (аккаунт, Wi‑Fi, имена «Улица» / «Подъезд» или как у вас).
2. В HA: **Настройки → Устройства и службы → Добавить интеграцию → Ezviz**.
3. Войдите тем же логином/паролем, что в приложении Ezviz.
4. Выберите обе камеры.

После добавления появятся сущности вида `camera.cs_c6_…` и `binary_sensor.…_motion_alarm` (точные имена зависят от модели).

### Переименование (обязательно для дашборда)

**Настройки → Устройства и службы → Сущности** — для каждой камеры:

| Было (пример) | Стало `entity_id` |
|---------------|-------------------|
| camera.cs_c6_xxxx | `camera.ezviz_ulica` |
| camera.cs_c6_yyyy | `camera.ezviz_podezd` |
| binary_sensor.…_motion_alarm (улица) | `binary_sensor.ezviz_ulica_motion_alarm` |
| binary_sensor.…_motion_alarm (подъезд) | `binary_sensor.ezviz_podezd_motion_alarm` |

Если у камеры нет `binary_sensor` движения — включите **обнаружение движения** в приложении Ezviz и перезагрузите интеграцию.

### Поток видео (нужен RTSP)

Интеграция HA **Ezviz** для live-потока требует локальный RTSP (порт **554**). Пока он закрыт — камеры в HA есть, но видео чёрное.

| Камера | Серийник | IP | Verification code |
|--------|----------|-----|-------------------|
| Улица | BF0241992 | 192.168.1.56 | **BNATXF** |
| Подъезд | BF5488322 | 192.168.1.119 | **PPNTGB** |

Проверка с HA: `timeout 2 bash -c 'echo >/dev/tcp/192.168.1.56/554'` → должно быть **open**.

После открытия 554 — завершить pending flows:

```bash
scp root@100.80.133.85:/config/secrets.yaml /tmp/ha_secrets_ezviz.yaml
HA_SECRETS=/tmp/ha_secrets_ezviz.yaml python3 tools/ha_ezviz_setup.py
```

В дашборде: `camera_view: live`. Опционально HACS: **WebRTC Camera**.

---

### Включить RTSP — способы (по документации Ezviz и форумам)

**Способ A — мобильное приложение** (если LAN Live View пускает):

Профиль → Настройки → **LAN Live View** → сканирование → камера → шестерёнка → **Local Service Settings** → RTSP **ON** → Save.

Ручной ввод (если скан не находит): IP, порт **8000**, логин `admin`, пароль = verification code (не пароль аккаунта!).

Ошибка **330007** = неверный код или перепутанные камеры. Телефон только в домашнем Wi‑Fi.

Обход бага русской версии (IP не вставляется): сохранить IP в **Контактах**, вставить оттуда.

**Способ B — EZVIZ PC Studio** (рекомендуется, если приложение даёт 330007):

Официальная инструкция: [Advanced Settings в EZVIZ Studio](https://support.ezviz.com/faq/article/How-to-visit-the-Advanced-Settings-of-EZVIZ-Studio)

1. Windows ПК в той же сети, что камеры.
2. Скачать [EZVIZ Studio](https://support.ezviz.com/download), войти в аккаунт Ezviz.
3. Закрыть Studio. Файл `config\AppConfig.ini` (обычно `C:\Program Files (x86)\Ezviz Studio\config\`), добавить:

   ```ini
   [LocalOperation]
   Show=1
   ```

4. Перезапустить Studio → у камеры появится **Advanced** → ввести verification code.
5. **Network → General** — порт RTSP **554** → **Apply**.
6. Если 554 не открывается: поставить **553**, Apply **без** перезагрузки, затем снова **554** и перезагрузить камеру (трюк из [issue HA #86204](https://github.com/home-assistant/core/issues/86204)).
7. **Network → NAT** — включить **UPnP** → Apply.

**Способ C — iVMS-4200** (Hikvision, та же сеть): иногда даёт доступ к сетевым настройкам, если Studio недоступен.

**Способ D — откат прошивки** (крайний случай для CS-H1c V5.3.8):

Если в Advanced нет RTSP — Ezviz отключил его в новых прошивках. Нужна полная модель из приложения (**О устройстве**, например `CS-H1c-…`).

Скачать старую `.dav`:

`https://usdownload.ezvizlife.com/device/<МОДЕЛЬ>/2.0/<МОДЕЛЬ>.dav`

или без `/2.0/` — зависит от модели. Прошить в Studio: **Advanced → System → System Maintenance → Upgrade**.

После включения RTSP отключить автообновление прошивки в приложении. Часть пользователей блокирует камерам интернет в роутере, чтобы облако не выключало RTSP снова.

**Модель CS-H1c** не в [списке ONVIF Ezviz](https://support.ezviz.com/faq/article/Whether-EZVIZ-devices-support-ONVIF-protocol) — только RTSP, не ONVIF.

---

## 2. Деплой панели на armbian

С VPS или ПК (SSH к `100.80.133.85:22222`):

```bash
cd /root/projects/empire
bash deploy/ha_deploy_wall_dashboard.sh
```

Скрипт копирует тему, дашборд, пакет Ezviz, патчит `configuration.yaml`, перезапускает HA.

Открыть: `http://192.168.1.41:8123/empire-wall/dom` (или Tailscale `100.80.133.85`).

---

## 3. HACS-карточки (если ещё нет)

**HACS → Frontend:**

- [Mushroom](https://github.com/piitaya/lovelace-mushroom) — кнопки, свет, chips, заголовки
- [mini-graph-card](https://github.com/kalkih/mini-graph-card) — sparkline-графики климата
- [card-mod](https://github.com/thomasloven/lovelace-card-mod) — glassmorphism, градиент фона (опционально, но рекомендуется)

После установки: **Настройки → Панели управления → Ресурсы** — убедиться, что `/hacsfiles/...` на месте (HACS обычно добавляет сам).

---

## 4. Планшет на стене (kiosk)

1. Установить **Home Assistant Companion** (Android) или **Fully Kiosk Browser**.
2. URL: `http://192.168.1.41:8123/empire-wall/dom`
3. В профиле HA на планшете: тема **empire_wall**.
4. Fully Kiosk: включить kiosk mode, keep screen on, скрыть системную панель.
5. Закрепить планшет статический IP в роутере.

Вкладка **Камеры** (`/empire-wall/kamery`) — полноэкранная сетка 2×1 для двух Ezviz.

---

## 5. Telegram при движении

Пакет `empire_ezviz.yaml` шлёт в Telegram (через `rest_command.empire_telegram`):

- движение на каждой камере отдельно;
- в режиме **Отпуск** — усиленное уведомление с любой камеры.

Проверка: **Настройки → Автоматизации** → «Ezviz — движение (улица)» — пройти перед камерой.

Если автоматизация в состоянии `unavailable` — неверный `entity_id` binary_sensor; переименуйте по §1.

---

## 6. Ручная настройка (без скрипта)

В `/config/configuration.yaml`:

```yaml
frontend:
  themes: !include_dir_merge_named themes

lovelace:
  mode: storage
  dashboards:
    empire-wall:
      mode: yaml
      title: Панель
      icon: mdi:tablet-dashboard
      show_in_sidebar: true
      require_admin: false
      filename: dashboards/empire_wall.yaml
```

Скопировать файлы из `homeassistant/{themes,dashboards,packages}/` в `/config/`.

---

## 7. Частые проблемы

| Симптом | Решение |
|---------|---------|
| Чёрный экран камеры | Включить RTSP (§1); порт 554 open; `ha_ezviz_setup.py` для pending flows |
| Ошибка 330007 в приложении | `admin` + verification code, порт 8000; сверить BNATXF/PPNTGB с наклейками |
| `invalid_host` в HA flow | RTSP ещё выключен на камере — сначала Способ B (PC Studio) |
| `without configuration` в логах | Завершить 2 pending Ezviz flows (admin + код) |
| Переименование entity | Переименовать `camera.ezviz_*`; проверить Ezviz в приложении онлайн |
| `Entity not found` | Имена в YAML ≠ реальные entity_id |
| Карточки «Custom element doesn't exist» | Установить Mushroom / mini-graph через HACS |
| Нет движения в Telegram | Переименовать `binary_sensor.*_motion_alarm`; включить детекцию в Ezviz |
| Медленный поток | Облако Ezviz; опционально WebRTC Camera (HACS) |

---

## Связанные документы

- `docs/TZ_HOME_ASSISTANT.md` — фаза 3 (Ezviz)
- `docs/HA_MVP_SETUP.md` — Telegram, ZHA
- `homeassistant/dashboards/empire_main.yaml` — дашборд по комнатам
