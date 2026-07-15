# Empire — инфраструктура: документация и восстановление

**Назначение:** один вход для всего, что не «контент gdepar», а **сеть, VPS, бэкапы, восстановление**.

| Документ | Когда читать |
|----------|--------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Схема: что где крутится, IP, порты |
| [HOME_NETWORK.md](HOME_NETWORK.md) | Flint 2, Keenetic, Wi‑Fi, podkop, Amnezia, USB |
| [VPS_RUNBOOK.md](VPS_RUNBOOK.md) | Поднять Empire с нуля на VPS |
| [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) | Яндекс.Диск, rclone, что куда, как откатить |
| [CHECKLIST_AFTER_DISASTER.md](CHECKLIST_AFTER_DISASTER.md) | Пошагово после поломки / нового VPS |

**На Яндекс.Диске (rclone `yandex:`):**

```
VPS-backup/<hostname>/latest/
  empire/              # код + docs/infra/
  etc-empire.tar.gz    # /etc/empire (секреты)
  systemd/             # empire*.service + timers
  sqlite-backups/      # empire.db снимки
  infra/               # снимок домашней сети + flint2 (если доступен)
```

**Быстрый бэкап вручную:**

```bash
cd /root/projects/empire
sudo bash scripts/infra/infra_backup_bundle.sh    # собрать infra + роутер
sudo bash scripts/vps_backup_to_yandex.sh         # на Я.Диск
```

**Быстрое восстановление VPS:**

```bash
sudo bash scripts/infra/vps_restore_from_yandex.sh latest
```

Подробности: [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).
