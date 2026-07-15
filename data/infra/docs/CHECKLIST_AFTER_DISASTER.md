# Чеклист после аварии

Отмечайте по порядку. Время — ориентир.

## A. «Не работает интернет дома» (15–30 мин)

- [ ] Ping `192.168.1.1` с ПК
- [ ] `ssh root@192.168.1.1` или через HA `100.80.133.85`
- [ ] `/etc/init.d/dnsmasq status` → если not running: `logread | grep dnsmasq`
- [ ] Удалить `/etc/dnsmasq.d/ai-vpn.nftset` если нет dnsmasq-full
- [ ] `/etc/init.d/podkop restart`
- [ ] YouTube на телефоне / Salut TV
- [ ] Amnezia на **ПК выключена**

## B. «VPS недоступен / новый сервер» (1–3 ч)

- [ ] `rclone lsd yandex:VPS-backup/`
- [ ] `scripts/infra/vps_restore_from_yandex.sh latest`
- [ ] venv + pip install
- [ ] systemd enable empire_*
- [ ] certbot nginx
- [ ] `curl gdepar.ru/api/gdepar/health`
- [ ] Tailscale `empire-vps-ts`
- [ ] Telegram-бот отвечает

## C. «Flint сгорел / сброс» (1–2 ч)

- [ ] Прошивка OpenWrt 24.10.4 sysupgrade
- [ ] UCI из `infra/home-router/` или bootstrap `00-bootstrap.sh`
- [ ] Amnezia `client.env` из бэкапа
- [ ] USB + `12-usb-samba-transmission.sh`
- [ ] Проверка: YouTube, TG, `\\192.168.1.1\download`

## D. «HA не доступен удалённо»

- [ ] LAN: http://192.168.1.41:8123
- [ ] Tailscale на HA: `100.80.133.85`
- [ ] GDrive backup restore: `docs/HA_TOX1_RECOVER.md`

## E. «Бэкапы не идут»

- [ ] `rclone lsd yandex:` — ошибка auth → `/etc/empire/rclone.env`
- [ ] `empire_unblock_backups.sh`
- [ ] `tmux attach -t empire-backups` — смотреть лог
- [ ] Место на диске: `df -h /`

## F. Контакты и пароли

| Что | Где |
|-----|-----|
| Flint root | `/root/.flint-admin.env` (VPS) |
| Keenetic (архив) | `/root/.keenetic-admin.env` |
| Empire env | `/etc/empire/` + бэкап tar |
| Яндекс rclone | `/etc/empire/rclone.env` |

## После восстановления

- [ ] Ручной бэкап: `infra_backup_bundle.sh` + `vps_backup_to_yandex.sh`
- [ ] Записать в Obsidian / checkpoint что сломалось и что сделали
