# Даунгрейд Aeza VIEs-3 → VIEs-2 без потери данных

**Сейчас:** прод на VIEs-2 `138.124.90.47` (rough-beige)  
**Старый:** VIEs-3 `193.233.232.48` — сервисы остановлены, ждать удаления в Aeza после проверки.

Диск Aeza **не сжимают**. Клон `dd` только на диск ≥ исходного  
([wiki Aeza](https://wiki.aeza.ru/guides/disk-transfer/)).  
Нужен **новый VPS + rsync/tar**, старый гасить после проверки.

Скрипт: `scripts/infra/vps_downgrade_migrate.sh`

**Cutover 2026-09-17:** Cloudflare → NEW; Flint tunnel → NEW; OLD nginx/apps/timers stopped.

---

## Что подготовить тебе

1. В кабинете Aeza заказать **VIEs-2, Вена**, Ubuntu 22.04/24.04.  
2. **Не удалять** старый сервер.  
3. Прислать агенту:
   - IP нового VPS  
   - SSH: `root` + **приватный ключ** (или пароль один раз)  
   - подтверждение, что DNS пока не трогаешь  

Агент выполнит `preflight → sync → activate → verify`.

---

## Чеклист (агент)

| # | Шаг | Команда / действие |
|---|-----|-------------------|
| 1 | Preflight место/SSH | `NEW_HOST=root@IP NEW_SSH_KEY=… bash scripts/infra/vps_downgrade_migrate.sh preflight` |
| 2 | Ночной/ручной бэкап на Я.Диск | `rclone` `pre-downgrade/` (на OLD) |
| 3 | Sync код+секреты+nginx+LE+systemd | `… sync` |
| 4 | Пакеты, venv, сервисы на NEW | `… activate` |
| 5 | Healthcheck | `… verify` |
| 6 | **Ты:** Cloudflare A → NEW_IP | neverretire.ru, gdepar.ru, www |
| 7 | **Ты/агент:** Flint Amnezia `:39182` + VLESS `:8443` → NEW_IP | см. `docs/FLINT2_AMNEZIA.md` |
| 8 | Tailscale на NEW | `tailscale up` |
| 9 | Сутки ок → удалить OLD в Aeza | |

---

## Что переносится

- `/root/projects/empire`, `/root/projects/kalitka` (snegiri и все линейки внутри empire)
- `/etc/empire`, `.env`, rclone, SSH keys
- nginx + Let’s Encrypt
- systemd `empire*`
- бэкапы `/var/backups/empire` (свежие)
- Docker Amnezia volume (если есть) / иначе переустановка контейнера

## Что обновляется после смены IP

- Cloudflare DNS  
- Flint: Amnezia `Endpoint`, VLESS Reality  
- Документы/скрипты с захардкоженным `193.233.232.48`  
- Tailscale ACL / имя `empire-vps-ts` при необходимости  

## Не делать

- Удалять OLD до зелёного verify + DNS  
- `dd` на меньший диск  
- Переустанавливать ОС на OLD «для экономии»
