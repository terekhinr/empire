# TOX1: восстановление после «мёртвого» Armbian

## Что случилось

- Установка на eMMC **не выполнялась** — зависли на `systemctl stop docker` (HA Supervised).
- **eMMC (Android) не перезаписывалась** — бэкап 30 ГБ на VPS цел.
- Скорее всего «умерла» **система на microSD** (зависшая остановка Docker).

## Что не потеряно

| Данные | Где |
|--------|-----|
| Android eMMC | на боксе + образ `/root/tox1-backup/tox1-emmc-android-20260606.img` на VPS |
| Конфиги empire (HA yaml, packages) | git-репозиторий `empire` |
| Бэкап HA | Google Drive (аддон `hassio_google_drive_backup`) |

---

## План A — быстрый (новая SD, HA из Google)

### 1. Проверить, что железо живо

1. **Вынуть microSD**.
2. Включить TOX1 (HDMI + LAN) → должен загрузиться **Android**.
3. Если Android есть — железо OK, идём дальше.

### 2. Записать свежий Armbian на microSD (с ПК)

Скачать образ **s905x3-tox1** (работает из коробки, DTB TOX1):

- Релизы: https://github.com/ophub/amlogic-s9xxx-armbian/releases  
- Искать: `s905x3-tox1` или `tox1`  
- Пример: `Armbian_*_amlogic_s905x3-tox1_*_6.18.19_server_*.img.gz`

Запись: **Balena Etcher** или `dd` → microSD **32 ГБ A2** (лучше новая карта).

### 3. Первая загрузка

1. Вставить SD, включить (USB 2.0 порт для прошивки не нужен — только для UBT).
2. Логин: `root` / `1234` → сменить пароль.
3. Сеть: Ethernet должен подняться сам; Wi‑Fi — см. `tox1-wireless` (issue ophub #3441).

### 4. Docker + HA Supervised

См. `docs/HA_ARMBIAN_DOCKER.md`.

### 5. Восстановить HA

- **Google Drive Backup** → Restore последний снапшот с мёртвого бокса.
- Или вручную: скопировать `/config` из бэкапа.

### 6. Деплой пакетов empire с VPS

```bash
# с машины, где есть репозиторий empire и SSH на новый armbian
rsync -av homeassistant/packages/ root@NEW_IP:/usr/share/hassio/homeassistant/packages/
```

Пароль root, Tailscale, Telegram — заново по `docs/HA_TELEGRAM_FIX.md`, `docs/HA_DOCKER_TAILSCALE.md`.

---

## План B — сразу на eMMC (после плана A)

Когда Armbian на SD снова стабилен:

```bash
# на боксе — БЕЗ systemctl stop docker
printf '526\n1\n' | armbian-install
poweroff
# вынуть SD, включить
```

Бэкап Android уже на VPS — не обязателен повторять.

---

## План C — только Android

Если HA не нужен срочно: SD не вставлять, пользоваться Android. Armbian — позже.

---

## План D — крайний случай (не грузится вообще)

1. **USB Burning Tool** + stock ROM TOX1 (4PDA / ophub issue #3441).
2. Восстановить Android из образа на VPS (`dd` на eMMC) — только если UBT не помог.

---

## После восстановления

- Не запускать `systemctl stop docker` перед `armbian-install`.
- SD держать как rescue ещё 1–2 недели после успешного eMMC.
- Metrika, KeenDNS, empire packages — по чеклисту `docs/EMPIRE_PIPELINE_CHECKLIST.md`.
