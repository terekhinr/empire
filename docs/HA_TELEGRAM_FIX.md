# Telegram из Home Assistant — устранение timeout

## Симптомы

- Всплывающее: **Таймаут при запросе** `https://api.telegram.org/bot.../sendMessage`
- Сообщение с VPS («Прямой тест API») **приходит**, из HA — **нет**

## Причина

С **armbian** (Home Assistant) **нет доступа** к `api.telegram.org` (блокировка, Docker, DNS).  
С **VPS empire** Telegram **работает** → шлём через **мост по Tailscale**.

## Решение: мост `ha_telegram_bridge` на VPS

### На VPS (empire)

1. В `.env` добавить:
   ```env
   HA_NOTIFY_TOKEN=придумайте_длинный_секрет_32символа
   HA_NOTIFY_PORT=8766
   ```
2. Запустить сервис:
   ```bash
   sudo cp deploy/empire_ha_notify.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now empire_ha_notify
   curl -s http://127.0.0.1:8766/health
   ```
3. Tailscale IP VPS (например `100.84.19.35`) — в панели Tailscale.

### На Home Assistant

1. `secrets.yaml`:
   ```yaml
   ha_notify_url: "http://100.84.19.35:8766/notify"
   ha_notify_token: "Bearer тот_же_секрет_что_HA_NOTIFY_TOKEN"
   ```
2. Обновить `packages/empire_automations.yaml` из репозитория.
3. Перезапуск HA → сценарий «Empire — тест Telegram».

---

## Устаревшее (прямой api.telegram.org)

1. Интеграция **`telegram_bot` в yaml** — убрать.
2. **`telegram_send_url`** — не работает с armbian при timeout.

## Решение (по порядку)

### 1. `secrets.yaml`

```yaml
telegram_send_url: "https://api.telegram.org/bot<ВАШ_ТОКЕН>/sendMessage"
```

Токен = строка из `TELEGRAM_TOKEN` в empire `.env`.  
Кавычки обязательны. **Без** минуса у chat_id в payload (уже 497498662 в yaml).

Удалите или закомментируйте старый блок `telegram_bot:` из `empire_notify.yaml` (оставьте файл-пустышку из репо).

### 2. `empire_automations.yaml`

Скопировать актуальный файл из репозитория (с `rest_command`, `timeout: 30`).

### 3. Перезапуск

**Настройки → Система → Перезапуск Home Assistant** (не только YAML).

### 4. Проверка сети из HA

Дополнение **Terminal** (на armbian):

```bash
curl -m 10 -sS "https://api.telegram.org/bot<ТОКЕН>/getMe"
```

- Если **ошибка** — у Docker HA нет выхода в интернет (DNS, firewall, прокси). Нужно починить сеть контейнера или `network_mode: host` в compose.
- Если **ok** — снова запустите сценарий «Empire — тест Telegram».

### 5. Repairs (target)

**Настройки → Устранение проблем** → предупреждение про `target` → **Игнорировать** после удаления `telegram_bot` из yaml, либо **Удалить** старую интеграцию Telegram Bot в **Устройства и службы**, если осталась от UI.

## Проверка без сценария

**Инструменты разработчика → Действия:**

- Служба: `rest_command.empire_telegram`
- Данные: `message: тест`

## Альтернатива

Пока HA не ходит в интернет: уведомления только через **empire-бот** (уже работает); автоматизации HA — после починки сети.
