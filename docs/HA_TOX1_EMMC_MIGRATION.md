# TOX1: перенос Armbian + HA на eMMC (с бэкапом Android)

## Текущая схема

| Носитель | Устройство | Содержимое |
|----------|------------|------------|
| microSD 15 ГБ | `mmcblk1` | Armbian + Docker + HA (**сейчас грузится отсюда**) |
| eMMC 29 ГБ | `mmcblk2` | Android (будет перезаписан) |

## Что будет сделано

1. **Бэкап eMMC** (~29 ГБ raw, ~2–3 ч) → VPS `/root/tox1-backup/`
2. **`armbian-install`** ID **526** (TOX1), ext4 — копия текущей системы на eMMC
3. **Выключение** → вынуть SD → включить → boot с eMMC

Docker, HA, конфиги, Tailscale — копируются вместе с rootfs.

## Скрипты на VPS (`moderate-amethys`)

| Скрипт | Действие |
|--------|----------|
| `/root/tox1-backup/01-backup-emmc.sh` | только бэкап |
| `/root/tox1-backup/02-install-emmc.sh` | только установка (после `.done` бэкапа) |
| `/root/tox1-backup/run-migration-night.sh` | бэкап + установка подряд |

Логи: `/root/tox1-backup/backup-YYYYMMDD.log`, `install-*.log`, `migration-*.log`.

Артефакты:

- `tox1-emmc-android-YYYYMMDD.img.gz` + `.sha256`

## Запуск ночью (рекомендуется)

**Запланировано на VPS:** `at` job #3 — **ночь 8→9 июня, 01:05 MSK** (22:05 UTC 8 июня). Бэкап уже есть (30 ГБ); ночью только **install** (~45 мин) → **~02:00 MSK** готово.

```bash
# на VPS
chmod +x /root/tox1-backup/*.sh
atq                    # посмотреть job
atrm N                 # отменить job N

# вариант A: всё одной командой (~3–4 ч, HA недоступен с момента install)
nohup /root/tox1-backup/run-migration-night.sh &

# вариант B: только бэкап сегодня, install завтра
nohup /root/tox1-backup/01-backup-emmc.sh &
# после backup-YYYYMMDD.done:
nohup /root/tox1-backup/02-install-emmc.sh &
```

Проверка прогресса бэкапа:

```bash
ls -lh /root/tox1-backup/tox1-emmc-android-*.img
tail -f /root/tox1-backup/backup-*.log
```

## После установки (утром)

1. **Вынуть microSD** из слота TOX1
2. Включить питание (HDMI лучше подключить — без него иногда зависает загрузка)
3. Подождать ~5–7 мин первый boot
4. Проверить:
   - `ssh root@100.80.133.85` (Tailscale)
   - `http://192.168.1.41:8123`
5. WiFi: сервис `tox1-wireless.service` должен переехать с системой

## Восстановление Android из бэкапа

На VPS (образ уже там):

```bash
# разархивировать при необходимости
gunzip -k /root/tox1-backup/tox1-emmc-android-YYYYMMDD.img.gz

# залить обратно (бокс должен грузиться с SD/USB с Armbian)
sshpass ssh root@100.80.133.85 \
  "dd if=/dev/zero of=/dev/mmcblk2 bs=16M count=1; dd of=/dev/mmcblk2 bs=16M"
# с VPS на armbian:
dd if=/root/tox1-backup/tox1-emmc-android-YYYYMMDD.img bs=16M | \
  ssh root@100.80.133.85 dd of=/dev/mmcblk2 bs=16M conv=fsync
```

Либо **stock ROM + USB Burning Tool** — см. `docs/HA_ARMBIAN_TOX1.md`.

## Откат без eMMC

Пока есть microSD с текущей системой — **вставить SD** → снова грузится старый Armbian (eMMC не трогать до успешной проверки новой системы).

**Совет:** не форматировать SD, пока eMMC + HA не проверены 1–2 дня.

## Риски

- ~3 ч простоя HA (бэкап + install)
- при обрыве питания во время `armbian-install` — восстановление из SD или UBT
- на eMMC ~29 ГБ — комфортнее, чем SD 15 ГБ
