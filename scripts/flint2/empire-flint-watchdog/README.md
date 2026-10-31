# Empire Flint Watchdog

Локальный сторож на Flint (OpenWrt). VPS не обязателен.

## Поведение

| Что | Как |
|-----|-----|
| **Автопочинка** | Каждые 5 мин: podkop/VLESS, маршруты, zapret, DNS, YouTube, Gemini, awg0, **USB NTFS, Samba `\\192.168.1.1\download`**, wsdd |
| **USB keep-alive** | Каждую минуту в `empire-lan-watch.sh`: remount по UUID + start smbd |
| **Тихий cron** | Лог только в `/tmp/empire-flint-watchdog.log`, stdout пустой |
| **Telegram** | **Выкл** для починок. Сводка — утро/вечер `empire-status-digest` на VPS |
| **Минута** | `empire-lan-watch.sh` — dedupe sing-box, fwmark, patch, USB/Samba (без TG) |

Настройка TG: `/etc/empire-flint-ui.env` — `HA_URL`, `HA_TOKEN`.

## Установка

С VPS (reverse SSH `:6223`):

```bash
bash scripts/flint2/empire-flint-watchdog/install.sh
```

На Flint:

```sh
sh empire-flint-watchdog/install-local.sh
```

## Команды

```sh
/usr/sbin/empire-flint-watchdog          # cron: тихо + TG при починке
/usr/sbin/empire-flint-watchdog --check  # только проверка, вывод в терминал
/usr/sbin/empire-flint-watchdog --force  # игнор cooldown
EMPIRE_FLINT_VERBOSE=1 empire-flint-watchdog  # лог в stdout
```

Состояние: `/tmp/empire-flint-watchdog.state`
