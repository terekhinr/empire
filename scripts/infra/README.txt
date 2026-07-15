# Infra scripts — бэкап и восстановление

| Скрипт | Назначение |
|--------|------------|
| `infra_backup_bundle.sh` | docs + nginx + systemd + rclone.conf + Flint UCI |
| `home_router_backup.sh` | Только Flint через HA |
| `vps_restore_from_yandex.sh` | Восстановление с `yandex:VPS-backup/.../latest/` |

Документация: `docs/infra/README.md`

```bash
sudo bash scripts/infra/infra_backup_bundle.sh
sudo bash scripts/vps_backup_to_yandex.sh
sudo bash scripts/infra/vps_restore_from_yandex.sh latest
```
