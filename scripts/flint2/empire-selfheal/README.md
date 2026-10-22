# Empire self-heal (Flint + VPS)

Паттерн как у OpenWrt UCI **apply → confirm → rollback** + monit/`flock`:

1. **Last-Known-Good** (`/etc/podkop/sing-box.golden.json`) — откат без `podkop restart`
2. **flock** `/var/lock/empire-heal.lock` — один хилер за раз
3. **дедуп cron** — один канонический набор задач
4. **smoke** — FakeIP TG/YT/AI + HTTP
5. **VPS remote** — reverse SSH `:6223`, алерт в Telegram если не ожили

## Flint

| Скрипт | Роль |
|--------|------|
| `/usr/sbin/empire-singbox-lkg` | smoke / save / restore / ensure |
| `/usr/sbin/empire-cron-normalize` | свести crontab |
| `/etc/podkop/empire-lan-watch.sh` | каждую минуту: USB + LKG если FakeIP мёртв |
| `/usr/sbin/empire-flint-watchdog` | раз в 5 мин полный heal |

## VPS

```bash
systemctl status empire-flint-remote-heal.timer
journalctl -u empire-flint-remote-heal.service -n 50
```

Деплой: `sh scripts/flint2/empire-selfheal/deploy-flint-selfheal.sh`
